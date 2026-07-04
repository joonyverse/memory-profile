import React, { useState } from "react";
import { ArrowLeftRight, X } from "lucide-react";
import StructTree from "./StructTree";

const LayoutDiff = ({ allConfigs, onClose }) => {
  if (!allConfigs || allConfigs.length === 0) return null;
  const structName = allConfigs[0].name;

  const [compilerA, setCompilerA] = useState("gcc");
  const [archA, setArchA] = useState("x86_64");
  const [compilerB, setCompilerB] = useState("gcc");
  const [archB, setArchB] = useState("arm64");

  // Find the selected configurations
  const structA = allConfigs.find(s => s.compiler === compilerA && s.arch === archA) || allConfigs[0];
  const structB = allConfigs.find(s => s.compiler === compilerB && s.arch === archB) || allConfigs[0];

  // Calculate diff stats
  const sizeDiff = structB.totalSize - structA.totalSize;
  const wasteDiff = (structB.wastePct - structA.wastePct).toFixed(1);
  const holesDiff = structB.holes - structA.holes;

  return (
    <div className="layout-diff-overlay" onClick={onClose}>
      <div className="layout-diff-panel glass-panel" onClick={(e) => e.stopPropagation()}>
        <div className="diff-panel-header">
          <div className="diff-title-group">
            <ArrowLeftRight size={20} className="icon-primary" />
            <h3>Layout Comparison: {structName}</h3>
          </div>
          <button onClick={onClose} className="btn-close-diff">
            <X size={18} />
          </button>
        </div>

        <div className="diff-stats-row">
          <div className="diff-stat-card">
            <span className="diff-stat-label">Size Comparison</span>
            <span className="diff-stat-val">
              {structA.totalSize}B <span className="diff-arrow">→</span> {structB.totalSize}B
            </span>
            <span className={`diff-stat-change ${sizeDiff <= 0 ? "good" : "bad"}`}>
              {sizeDiff === 0 ? "No change" : sizeDiff < 0 ? `${sizeDiff}B (Reduced)` : `+${sizeDiff}B (Increased)`}
            </span>
          </div>
          <div className="diff-stat-card">
            <span className="diff-stat-label">Waste Percentage</span>
            <span className="diff-stat-val">
              {structA.wastePct.toFixed(1)}% <span className="diff-arrow">→</span> {structB.wastePct.toFixed(1)}%
            </span>
            <span className={`diff-stat-change ${parseFloat(wasteDiff) <= 0 ? "good" : "bad"}`}>
              {parseFloat(wasteDiff) === 0 ? "No change" : parseFloat(wasteDiff) < 0 ? `${wasteDiff}% (Reduced)` : `+${wasteDiff}% (Increased)`}
            </span>
          </div>
          <div className="diff-stat-card">
            <span className="diff-stat-label">Holes Count</span>
            <span className="diff-stat-val">
              {structA.holes} <span className="diff-arrow">→</span> {structB.holes}
            </span>
            <span className={`diff-stat-change ${holesDiff <= 0 ? "good" : "bad"}`}>
              {holesDiff === 0 ? "No change" : holesDiff < 0 ? `${holesDiff} holes` : `+${holesDiff} holes`}
            </span>
          </div>
        </div>

        <div className="diff-panes-container">
          <div className="diff-pane">
            <div className="diff-pane-title">
              <span>Version A Controls</span>
              <div className="diff-controls-row">
                <select 
                  value={compilerA} 
                  onChange={(e) => setCompilerA(e.target.value)}
                  className="select-control compact"
                >
                  <option value="gcc">GCC</option>
                  <option value="clang">Clang</option>
                </select>
                <select 
                  value={archA} 
                  onChange={(e) => setArchA(e.target.value)}
                  className="select-control compact"
                >
                  <option value="x86_64">x86_64</option>
                  <option value="arm64">ARM64</option>
                </select>
              </div>
            </div>
            <div className="diff-tree-wrapper">
              <StructTree struct={structA} />
            </div>
          </div>

          <div className="diff-pane">
            <div className="diff-pane-title">
              <span>Version B Controls</span>
              <div className="diff-controls-row">
                <select 
                  value={compilerB} 
                  onChange={(e) => setCompilerB(e.target.value)}
                  className="select-control compact"
                >
                  <option value="gcc">GCC</option>
                  <option value="clang">Clang</option>
                </select>
                <select 
                  value={archB} 
                  onChange={(e) => setArchB(e.target.value)}
                  className="select-control compact"
                >
                  <option value="x86_64">x86_64</option>
                  <option value="arm64">ARM64</option>
                </select>
              </div>
            </div>
            <div className="diff-tree-wrapper">
              <StructTree struct={structB} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LayoutDiff;
