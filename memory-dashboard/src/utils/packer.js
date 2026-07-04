export const getAlignment = (item) => {
  if (item.type === "nested") {
    if (item.children && item.children.length > 0) {
      return Math.max(...item.children.map(getAlignment));
    }
    return 1;
  }
  const arrayMatch = item.decl.match(/\[(\d+)\]$/);
  if (arrayMatch) {
    const length = parseInt(arrayMatch[1], 10);
    const elementSize = length > 0 ? item.size / length : 1;
    return Math.min(elementSize, 8);
  }
  return Math.min(item.size, 8);
};

export const packLayout = (items) => {
  const activeItems = items.filter(item => item.type !== "hole" && item.type !== "padding");
  
  const processedItems = activeItems.map(item => {
    if (item.type === "nested" && item.children) {
      if (item.decl.includes("union")) {
        return {
          ...item,
          children: item.children.map(child => {
            if (child.type === "nested") {
              return packLayout([child]).layout[0];
            }
            return child;
          })
        };
      } else {
        return {
          ...item,
          children: packLayout(item.children).layout
        };
      }
    }
    return item;
  });

  const isUnion = processedItems.length > 1 && processedItems.every(item => item.offset === 0);
  
  let sortedItems = [...processedItems];
  if (!isUnion) {
    sortedItems.sort((a, b) => getAlignment(b) - getAlignment(a));
  }

  let currentOffset = 0;
  const newLayout = [];
  let maxAlign = 1;

  for (const item of sortedItems) {
    const align = getAlignment(item);
    maxAlign = Math.max(maxAlign, align);

    const paddingNeeded = (align - (currentOffset % align)) % align;
    if (paddingNeeded > 0) {
      newLayout.push({
        type: "hole",
        decl: "/* XXX " + paddingNeeded + " bytes hole */",
        offset: currentOffset,
        size: paddingNeeded
      });
      currentOffset += paddingNeeded;
    }

    if (item.type === "nested" && item.children) {
      const subOffset = currentOffset;
      const adjustedChildren = item.children.map(child => {
        return {
          ...child,
          offset: subOffset + (child.offset - item.offset)
        };
      });

      newLayout.push({
        ...item,
        offset: currentOffset,
        children: adjustedChildren
      });
      currentOffset += item.size;
    } else {
      newLayout.push({
        ...item,
        offset: currentOffset
      });
      currentOffset += item.size;
    }
  }

  const tailPadding = (maxAlign - (currentOffset % maxAlign)) % maxAlign;
  if (tailPadding > 0) {
    newLayout.push({
      type: "padding",
      decl: "/* padding: " + tailPadding + " bytes */",
      offset: currentOffset,
      size: tailPadding
    });
    currentOffset += tailPadding;
  }

  return {
    layout: newLayout,
    totalSize: currentOffset,
    maxAlign
  };
};

export const generateCppCode = (structName, layout) => {
  let indent = "    ";
  let code = "struct " + structName + " {\n";

  const formatItem = (item, depth) => {
    const curIndent = indent.repeat(depth);
    if (item.type === "hole" || item.type === "padding") {
      return "";
    }
    
    if (item.type === "nested") {
      let declName = item.decl.replace("struct/union", "").trim();
      let keyword = item.decl.includes("union") ? "union" : "struct";
      let lines = curIndent + keyword + " {\n";
      item.children.forEach(child => {
        lines += formatItem(child, depth + 1);
      });
      lines += curIndent + "} " + declName + ";\n";
      return lines;
    }

    return curIndent + item.decl + ";\n";
  };

  layout.forEach(item => {
    code += formatItem(item, 1);
  });

  code += "};";
  return code;
};
