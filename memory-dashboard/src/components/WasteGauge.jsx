import React, { useEffect, useState } from 'react';

const WasteGauge = ({ label, value }) => {
  const [width, setWidth] = useState(0);

  // Animate the bar width on load
  useEffect(() => {
    const timer = setTimeout(() => {
      setWidth(value);
    }, 100);
    return () => clearTimeout(timer);
  }, [value]);

  // Determine color based on value (similar to Grafana thresholds)
  let color = 'var(--accent-green)';
  if (value > 25) color = 'var(--accent-cyan)';
  if (value > 40) color = 'var(--accent-orange)';
  if (value > 60) color = 'var(--accent-red)';

  return (
    <div className="bar-row">
      <div className="bar-header">
        <span className="bar-label">{label}</span>
        <span className="bar-value" style={{ color }}>{value.toFixed(1)}%</span>
      </div>
      <div className="bar-track">
        <div 
          className="bar-fill" 
          style={{ 
            width: `${Math.min(width, 100)}%`, 
            background: `linear-gradient(90deg, transparent, ${color})` 
          }}
        ></div>
      </div>
    </div>
  );
};

export default WasteGauge;
