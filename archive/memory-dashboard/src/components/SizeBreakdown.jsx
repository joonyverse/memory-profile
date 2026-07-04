import React, { useEffect, useState } from 'react';

const SizeBreakdown = ({ label, members, holes, padding }) => {
  const [loaded, setLoaded] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoaded(true);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  const total = members + holes + padding;
  
  // Calculate percentages for the stacked bar
  const memPct = total > 0 ? (members / total) * 100 : 0;
  const holePct = total > 0 ? (holes / total) * 100 : 0;
  const padPct = total > 0 ? (padding / total) * 100 : 0;

  return (
    <div className="bar-row">
      <div className="bar-header">
        <span className="bar-label">{label}</span>
        <span className="bar-value">{total} B</span>
      </div>
      <div className="stacked-track">
        <div 
          className="stacked-segment segment-members" 
          style={{ width: loaded ? `${memPct}%` : '0%' }}
          title={`Members: ${members} B`}
        ></div>
        <div 
          className="stacked-segment segment-holes" 
          style={{ width: loaded ? `${holePct}%` : '0%' }}
          title={`Holes: ${holes} B`}
        ></div>
        <div 
          className="stacked-segment segment-padding" 
          style={{ width: loaded ? `${padPct}%` : '0%' }}
          title={`Padding: ${padding} B`}
        ></div>
      </div>
    </div>
  );
};

export default SizeBreakdown;
