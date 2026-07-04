"""
heap_tracker.py — GDB Python 기반 동적 힙 할당 추적기

malloc / operator new 호출을 후킹하여:
  1. 할당 크기를 캡처
  2. DWARF 디버그 정보에서 알려진 구조체 크기와 매칭
  3. 호출 스택(backtrace)에서 어떤 코드 경로에서 할당했는지 기록
  4. complete_cell_setup() 호출 시마다 해당 셀에서 할당된 구조체 요약 출력

사용법:
  gdb -batch -ex "source heap_tracker.py" -ex "quit" ./memory_profile_example
"""

import gdb
import os

# ============================================================
# 1단계: DWARF에서 알려진 struct/class 크기를 수집하여 크기→이름 맵 구축
# ============================================================
def build_size_to_struct_map():
    """structs_list.txt에서 구조체 이름을 읽고, DWARF에서 크기를 조회하여 매핑"""
    size_map = {}  # size → [name1, name2, ...]

    structs = []
    if os.path.exists("structs_list.txt"):
        with open("structs_list.txt", "r") as f:
            structs = [line.strip() for line in f if line.strip()]

    for sname in structs:
        t = None
        for prefix in ("", "struct ", "class "):
            try:
                t = gdb.lookup_type(prefix + sname)
                if t:
                    break
            except:
                pass
        if t is None:
            continue

        sz = t.sizeof
        if sz not in size_map:
            size_map[sz] = []
        size_map[sz].append(sname)

    return size_map


# ============================================================
# 2단계: 할당 이벤트 수집기 (전역 상태)
# ============================================================
class AllocationTracker:
    def __init__(self, size_map):
        self.size_map = size_map
        self.current_cell = 0
        self.cell_allocations = {}  # cell_id → [(size, matched_structs, caller)]
        self.pending_allocs = []    # 현재 셀에서 아직 cell_setup이 호출되기 전의 할당들

    def record_alloc(self, size, caller_info):
        matched = self.size_map.get(size, [])
        self.pending_allocs.append((size, matched, caller_info))

    def on_cell_setup(self, cell_id):
        self.current_cell = cell_id
        self.cell_allocations[cell_id] = list(self.pending_allocs)
        self.pending_allocs = []

    def print_cell_summary(self, cell_id):
        allocs = self.cell_allocations.get(cell_id, [])
        print(f"\n{'='*60}")
        print(f" Cell {cell_id} Dynamic Allocation Summary")
        print(f"{'='*60}")

        if not allocs:
            print("  (no allocations recorded)")
            return

        total_bytes = 0
        struct_counts = {}

        for size, matched, caller in allocs:
            total_bytes += size
            if matched:
                for name in matched:
                    struct_counts[name] = struct_counts.get(name, 0) + 1
            else:
                label = f"unknown ({size}B)"
                struct_counts[label] = struct_counts.get(label, 0) + 1

        print(f"  Total allocations: {len(allocs)}")
        print(f"  Total bytes: {total_bytes:,} bytes")
        print(f"")
        print(f"  {'Type':<35} {'Count':>5}  {'Size':>10}  {'Caller'}")
        print(f"  {'-'*35} {'-'*5}  {'-'*10}  {'-'*30}")

        for size, matched, caller in allocs:
            if matched:
                type_name = " / ".join(matched)
            elif size >= 1024 * 1024:
                type_name = f"raw buffer ({size / (1024*1024):.1f} MB)"
            elif size >= 1024:
                type_name = f"raw buffer ({size / 1024:.1f} KB)"
            else:
                type_name = f"unknown ({size}B)"

            print(f"  {type_name:<35} {'1':>5}  {size:>10,}  {caller}")

        print(f"")
        print(f"  Struct type breakdown:")
        for name, count in sorted(struct_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count}x")


# ============================================================
# 3단계: GDB Breakpoint 클래스 정의
# ============================================================
class MallocBreakpoint(gdb.Breakpoint):
    """malloc() 호출을 가로채서 할당 크기와 호출자를 기록"""
    def __init__(self, tracker):
        super().__init__("malloc", internal=True)
        self.tracker = tracker
        self.silent = True

    def stop(self):
        try:
            # malloc의 첫 번째 인자 = 할당 크기
            frame = gdb.selected_frame()
            size = int(frame.read_var("size")) if frame else 0
        except:
            try:
                # 레지스터에서 직접 읽기 (x86_64: rdi = 첫 번째 인자)
                size = int(gdb.parse_and_eval("$rdi"))
            except:
                size = 0

        if size > 0:
            caller = self._get_caller()
            self.tracker.record_alloc(size, caller)

        return False  # 실행 계속

    def _get_caller(self):
        try:
            frame = gdb.selected_frame()
            if frame:
                caller_frame = frame.older()
                if caller_frame:
                    sal = caller_frame.find_sal()
                    func_name = caller_frame.name() or "??"
                    if sal and sal.symtab:
                        return f"{func_name} ({sal.symtab.filename}:{sal.line})"
                    return func_name
        except:
            pass
        return "??"


class OperatorNewBreakpoint(gdb.Breakpoint):
    """operator new() 호출을 가로채서 할당 크기와 호출자를 기록"""
    def __init__(self, tracker):
        # operator new(unsigned long) 에 브레이크포인트
        super().__init__("operator new(unsigned long)", internal=True)
        self.tracker = tracker
        self.silent = True

    def stop(self):
        try:
            size = int(gdb.parse_and_eval("$rdi"))
        except:
            size = 0

        if size > 0:
            caller = self._get_caller()
            self.tracker.record_alloc(size, caller)

        return False

    def _get_caller(self):
        try:
            frame = gdb.selected_frame()
            if frame:
                caller_frame = frame.older()
                if caller_frame:
                    sal = caller_frame.find_sal()
                    func_name = caller_frame.name() or "??"
                    if sal and sal.symtab:
                        return f"{func_name} ({sal.symtab.filename}:{sal.line})"
                    return func_name
        except:
            pass
        return "??"


class CellSetupBreakpoint(gdb.Breakpoint):
    """complete_cell_setup() 호출 시 셀 ID를 캡처하고 할당 요약 출력"""
    def __init__(self, tracker):
        func_name = os.environ.get("CELL_SETUP_FUNC", "complete_cell_setup")
        super().__init__(func_name, internal=False)
        self.tracker = tracker
        self.silent = True

    def stop(self):
        try:
            cell_id = int(gdb.parse_and_eval("$rdi"))
        except:
            try:
                frame = gdb.selected_frame()
                cell_id = int(frame.read_var("cell_id"))
            except:
                cell_id = self.tracker.current_cell + 1

        self.tracker.on_cell_setup(cell_id)
        self.tracker.print_cell_summary(cell_id)

        return False  # 실행 계속


# ============================================================
# 4단계: 메인 실행
# ============================================================
def main():
    print("====================================================")
    print(" GDB Heap Allocation Tracker")
    print(" malloc/new → Struct Type Matching")
    print("====================================================")

    # DWARF에서 구조체 크기 맵 구축
    size_map = build_size_to_struct_map()
    print(f"\nKnown struct sizes from DWARF:")
    for sz in sorted(size_map.keys()):
        names = ", ".join(size_map[sz])
        print(f"  {sz:>6} bytes → {names}")

    # 추적기 초기화
    tracker = AllocationTracker(size_map)

    # 브레이크포인트 설정
    try:
        MallocBreakpoint(tracker)
        print("\n[OK] malloc() breakpoint set")
    except Exception as e:
        print(f"\n[WARN] Could not set malloc breakpoint: {e}")

    try:
        OperatorNewBreakpoint(tracker)
        print("[OK] operator new() breakpoint set")
    except Exception as e:
        print(f"[WARN] Could not set operator new breakpoint: {e}")

    try:
        CellSetupBreakpoint(tracker)
        print("[OK] Cell setup breakpoint set")
    except Exception as e:
        print(f"[WARN] Could not set cell setup breakpoint: {e}")

    print("\nStarting execution...\n")

main()
