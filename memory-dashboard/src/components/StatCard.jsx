import React from 'react';

const StatCard = ({ title, value, icon, colorClass, isString = false }) => {
  return (
    <div className="glass-panel stat-card">
      <div className="panel-title">
        {icon} {title}
      </div>
      <div className={`stat-value ${colorClass}`} style={isString ? { fontSize: '2rem' } : {}}>
        {value}
      </div>
    </div>
  );
};

export default StatCard;
