import React, { useState } from 'react';
import { CornerDownRight, ChevronRight, ChevronDown } from 'lucide-react';

const TreeNode = ({ item, depth, maxOffset }) => {
  const [expanded, setExpanded] = useState(false);
  const isHole = item.type === 'hole';
  const isPad = item.type === 'padding';
  const isNested = item.type === 'nested';
  
  // Handle Array matching
  const arrayMatch = !isHole && !isPad && !isNested ? item.decl.match(/(.*?)\[(\d+)\]$/) : null;
  const isArray = !!arrayMatch;
  const arrayLength = isArray ? parseInt(arrayMatch[2], 10) : 0;
  const elementSize = isArray ? item.size / arrayLength : 0;
  const arrayBaseName = isArray ? arrayMatch[1].trim() : '';

  const hasChildren = isNested && item.children && item.children.length > 0;
  const isExpandable = hasChildren || isArray;

  const rowClass = isHole ? 'code-row hole-row' : (isPad ? 'code-row pad-row' : 'code-row');

  let highlightedDecl = item.decl;
  if (!isHole && !isPad && !isNested) {
    const parts = item.decl.split(' ');
    const name = parts.pop();
    const typeStr = parts.join(' ');
    highlightedDecl = (
      <>
        <span className="type-str">{typeStr}</span>{' '}
        <span className="name-str">{name}</span>;
      </>
    );
  } else if (isNested) {
    highlightedDecl = (
      <>
        <span style={{ color: 'var(--accent-cyan)' }}>{item.decl}</span>{' {'}
      </>
    );
  }

  return (
    <>
      <div 
        className={rowClass} 
        onClick={() => isExpandable && setExpanded(!expanded)} 
        style={{ cursor: isExpandable ? 'pointer' : 'default' }}
      >
        <div className="code-col-decl" style={{ paddingLeft: `${depth * 20}px` }}>
          {isExpandable ? (
            expanded ? <ChevronDown size={14} className="indent-icon" /> : <ChevronRight size={14} className="indent-icon" />
          ) : (
            <CornerDownRight size={14} className="indent-icon" style={{ visibility: isHole || isPad ? 'hidden' : 'visible' }} />
          )}
          {highlightedDecl}
        </div>
        <div className="code-col-offset">{item.offset}</div>
        <div className="code-col-size">{item.size}</div>
        
        {maxOffset > 0 && (
          <div 
            className="inline-visual-bar" 
            style={{ 
              left: `${(item.offset / maxOffset) * 100}%`,
              width: `${(item.size / maxOffset) * 100}%`
            }} 
          />
        )}
      </div>
      
      {/* Recursively Render Children */}
      {expanded && isNested && item.children && (
        item.children.map((child, idx) => (
          <TreeNode key={`child-${idx}`} item={child} depth={depth + 1} maxOffset={maxOffset} />
        ))
      )}
      {expanded && isNested && (
        <div className="code-row">
          <div className="code-col-decl" style={{ paddingLeft: `${depth * 20}px` }}>
            <span style={{ color: 'var(--text-muted)' }}>{'}'}</span>
          </div>
        </div>
      )}

      {/* Dynamically Render Array Elements */}
      {expanded && isArray && (
        Array.from({ length: Math.min(arrayLength, 100) }).map((_, i) => (
          <div key={`arr-${i}`} className="code-row">
            <div className="code-col-decl" style={{ paddingLeft: `${(depth + 1) * 20}px` }}>
              <CornerDownRight size={14} className="indent-icon" style={{ opacity: 0.5 }} />
              {(() => {
                const parts = arrayBaseName.split(/\s+/);
                const varName = parts.pop();
                const typeStr = parts.join(' ');
                return (
                  <>
                    <span className="type-str">{typeStr}</span>{' '}
                    <span className="name-str">{varName}[{i}]</span>;
                  </>
                );
              })()}
            </div>
            <div className="code-col-offset">{item.offset + (i * elementSize)}</div>
            <div className="code-col-size">{elementSize}</div>
            {maxOffset > 0 && (
              <div 
                className="inline-visual-bar" 
                style={{ 
                  left: `${((item.offset + (i * elementSize)) / maxOffset) * 100}%`,
                  width: `${(elementSize / maxOffset) * 100}%`,
                  background: 'rgba(255, 255, 255, 0.1)'
                }} 
              />
            )}
          </div>
        ))
      )}
      {expanded && isArray && arrayLength > 100 && (
        <div className="code-row">
          <div className="code-col-decl" style={{ paddingLeft: `${(depth + 1) * 20}px` }}>
            <span className="comment">... {arrayLength - 100} more elements omitted ...</span>
          </div>
        </div>
      )}
    </>
  );
};

const StructTree = ({ struct }) => {
  if (!struct) return null;

  let layout = [];
  try {
    if (struct.layoutJson) {
      layout = JSON.parse(struct.layoutJson);
    }
  } catch (e) {
    console.error("Failed to parse layoutJson", e);
  }

  const maxOffset = struct.totalSize || (layout.length > 0 ? layout[layout.length - 1].offset + layout[layout.length - 1].size : 100);

  return (
    <div className="inline-struct-tree" onClick={e => e.stopPropagation()}>
      <div className="code-view">
        <div className="code-header-top">
          <span style={{ color: 'var(--accent-purple)' }}>struct</span> {struct.name} {'{'}
        </div>
        
        <div className="code-header">
          <span className="code-col-decl">Declaration</span>
          <span className="code-col-offset">Offset</span>
          <span className="code-col-size">Size</span>
        </div>
        
        <div className="code-body">
          {layout.map((item, idx) => (
            <TreeNode key={`root-${idx}`} item={item} depth={0} maxOffset={maxOffset} />
          ))}
        </div>
        <div className="code-footer">
          {'}'}; <span className="comment">/* size: {struct.totalSize} bytes, {struct.wastePct}% waste */</span>
        </div>
      </div>
    </div>
  );
};

export default StructTree;
