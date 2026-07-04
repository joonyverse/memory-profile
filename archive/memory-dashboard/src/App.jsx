import React, { useState, useEffect } from 'react';
import { InfluxDB } from '@influxdata/influxdb-client';
import { Activity, Database, AlertTriangle, GitCommit } from 'lucide-react';
import StatCard from './components/StatCard';
import WasteGauge from './components/WasteGauge';
import SizeBreakdown from './components/SizeBreakdown';
import StructTree from './components/StructTree';
import LayoutDiff from './components/LayoutDiff';


// Configure InfluxDB client to use the Vite proxy
const token = 'dev-token-123';
const org = 'memory-profile';
const bucket = 'pahole';
// Use the proxy configured in vite.config.js
const client = new InfluxDB({ url: '/api/influx', token: token });
const queryApi = client.getQueryApi(org);

function App() {
  const [loading, setLoading] = useState(true);
  const [expandedStructs, setExpandedStructs] = useState(new Set());
  const [compiler, setCompiler] = useState('gcc');
  const [arch, setArch] = useState('x86_64');
  const [compareStructName, setCompareStructName] = useState(null);
  const [compareData, setCompareData] = useState([]);
  const [data, setData] = useState({
    structs: [],
    totalWaste: 0,
    worstWastePct: 0,
    totalStructs: 0,
    latestCommit: 'Unknown'
  });

  const toggleStruct = (structName) => {
    setExpandedStructs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(structName)) {
        newSet.delete(structName);
      } else {
        newSet.add(structName);
      }
      return newSet;
    });
  };

  const handleCompare = async (structName) => {
    try {
      setCompareStructName(structName);
      // Fetch all configs for this struct from InfluxDB
      const query = `
        from(bucket: "${bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "struct_metrics")
          |> filter(fn: (r) => r.struct_name == "${structName}")
          |> filter(fn: (r) => r._field == "waste_pct" or r._field == "sum_members" or r._field == "sum_holes" or r._field == "padding_end" or r._field == "layout_json" or r._field == "total_size")
          |> group(columns: ["struct_name", "commit", "compiler", "arch", "_field"])
          |> last()
          |> pivot(rowKey: ["struct_name", "commit", "compiler", "arch"], columnKey: ["_field"], valueColumn: "_value")
      `;
      
      const results = [];
      for await (const { values, tableMeta } of queryApi.iterateRows(query)) {
        const row = tableMeta.toObject(values);
        results.push({
          name: row.struct_name,
          commit: row.commit,
          compiler: row.compiler,
          arch: row.arch,
          wastePct: row.waste_pct || 0,
          members: row.sum_members || 0,
          holes: row.sum_holes || 0,
          padding: row.padding_end || 0,
          totalSize: row.total_size || 0,
          layoutJson: row.layout_json || "[]"
        });
      }
      setCompareData(results);
    } catch (err) {
      console.error("Failed to fetch compare data", err);
    }
  };


  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const query = `
          from(bucket: "${bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "struct_metrics")
            |> filter(fn: (r) => r.compiler == "${compiler}")
            |> filter(fn: (r) => r.arch == "${arch}")
            |> filter(fn: (r) => r._field == "waste_pct" or r._field == "sum_members" or r._field == "sum_holes" or r._field == "padding_end" or r._field == "layout_json" or r._field == "total_size")
            |> group(columns: ["struct_name", "commit", "_field"])
            |> last()
            |> pivot(rowKey: ["struct_name", "commit"], columnKey: ["_field"], valueColumn: "_value")
        `;
        
        const results = [];
        for await (const { values, tableMeta } of queryApi.iterateRows(query)) {
          const row = tableMeta.toObject(values);
          results.push({
            name: row.struct_name,
            commit: row.commit,
            wastePct: row.waste_pct || 0,
            members: row.sum_members || 0,
            holes: row.sum_holes || 0,
            padding: row.padding_end || 0,
            totalSize: row.total_size || 0,
            layoutJson: row.layout_json || "[]"
          });
        }
        
        // Process results
        const sorted = results.sort((a, b) => b.wastePct - a.wastePct);
        const totalWastedBytes = sorted.reduce((acc, curr) => acc + curr.holes + curr.padding, 0);
        const worstWaste = sorted.length > 0 ? sorted[0].wastePct : 0;
        const latestCommit = sorted.length > 0 ? sorted[0].commit : 'No data';
        
        setData({
          structs: sorted,
          totalWaste: totalWastedBytes,
          worstWastePct: worstWaste,
          totalStructs: sorted.length,
          latestCommit: latestCommit
        });
        
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data from InfluxDB:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, [compiler, arch]);

  if (loading) {
    return (
      <div className="dashboard-container loading-container">
        <div className="spinner"></div>
        <p>Loading memory profile data...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-title">
          <Database size={28} className="icon-primary" />
          <h1>Memory Profile <span className="subtitle">— Pahole Analysis</span></h1>
        </div>
        <div className="header-controls">
          <div className="control-group">
            <label htmlFor="compiler-select">Compiler</label>
            <select 
              id="compiler-select" 
              value={compiler} 
              onChange={(e) => setCompiler(e.target.value)}
              className="select-control"
            >
              <option value="gcc">GCC</option>
              <option value="clang">Clang</option>
            </select>
          </div>
          <div className="control-group">
            <label htmlFor="arch-select">Architecture</label>
            <select 
              id="arch-select" 
              value={arch} 
              onChange={(e) => setArch(e.target.value)}
              className="select-control"
            >
              <option value="x86_64">x86_64</option>
              <option value="arm64">ARM64</option>
            </select>
          </div>
          <div className="header-status">
            <span className="status-dot"></span> Live Data
          </div>
        </div>
      </header>

      <main className="dashboard-content">
        <section className="grid-stats">
          <StatCard title="Total Structs" value={data.totalStructs} icon={<Database size={20} />} />
          <StatCard title="Total Wasted Bytes" value={data.totalWaste.toLocaleString()} icon={<Activity size={20} />} color="var(--accent-orange)" />
          <StatCard title="Worst Waste %" value={`${data.worstWastePct.toFixed(1)}%`} icon={<AlertTriangle size={20} />} color="var(--accent-red)" />
          <StatCard title="Latest Commit" value={data.latestCommit} icon={<GitCommit size={20} />} color="var(--accent-cyan)" />
        </section>

        <section className="grid-main">
          <div className="glass-panel">
            <h3 className="panel-title">Waste % by Struct (Click to Expand)</h3>
            <div className="bar-gauge-container">
              {data.structs.slice(0, 10).map((s, idx) => (
                <div key={`waste-${idx}`} className="expandable-wrapper">
                  <div onClick={() => toggleStruct(`waste-${s.name}`)} className="clickable-row" style={{ cursor: 'pointer' }}>
                    <WasteGauge label={s.name} value={s.wastePct} />
                  </div>
                  <div className={`expandable-content ${expandedStructs.has(`waste-${s.name}`) ? 'expanded' : ''}`}>
                    {expandedStructs.has(`waste-${s.name}`) && <StructTree struct={s} onCompare={handleCompare} />}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel">
            <h3 className="panel-title">Size Breakdown (Click to Expand)</h3>
            <div className="stacked-bar-container">
              {data.structs.slice(0, 10).map((s, idx) => (
                <div key={`size-${idx}`} className="expandable-wrapper">
                  <div onClick={() => toggleStruct(`size-${s.name}`)} className="clickable-row" style={{ cursor: 'pointer' }}>
                    <SizeBreakdown 
                      label={s.name} 
                      members={s.members} 
                      holes={s.holes} 
                      padding={s.padding} 
                    />
                  </div>
                  <div className={`expandable-content ${expandedStructs.has(`size-${s.name}`) ? 'expanded' : ''}`}>
                    {expandedStructs.has(`size-${s.name}`) && <StructTree struct={s} onCompare={handleCompare} />}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="legend">
              <div className="legend-item">
                <div className="legend-dot segment-members"></div> Members
              </div>
              <div className="legend-item">
                <div className="legend-dot segment-holes"></div> Holes
              </div>
              <div className="legend-item">
                <div className="legend-dot segment-padding"></div> Padding
              </div>
            </div>
          </div>
        </section>
      </main>
      {compareStructName && compareData.length > 0 && (
        <LayoutDiff 
          allConfigs={compareData} 
          onClose={() => {
            setCompareStructName(null);
            setCompareData([]);
          }} 
        />
      )}
    </div>
  );
}

export default App;
