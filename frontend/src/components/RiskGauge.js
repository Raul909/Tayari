'use client';

import { RISK_COLORS } from '@/lib/constants';

export default function RiskGauge({ probability, riskLevel }) {
  const percentage = Math.round(probability * 100);
  const color = RISK_COLORS[riskLevel] || RISK_COLORS.LOW;

  // SVG circle math
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (probability * circumference);

  return (
    <div className="risk-gauge">
      <svg className="risk-gauge-svg" viewBox="0 0 180 180">
        <circle
          className="risk-gauge-bg"
          cx="90"
          cy="90"
          r={radius}
        />
        <circle
          className="risk-gauge-fill"
          cx="90"
          cy="90"
          r={radius}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="risk-gauge-center">
        <div className="risk-gauge-value" style={{ color }}>
          {percentage}%
        </div>
        <div className="risk-gauge-label">Flood Risk</div>
      </div>
    </div>
  );
}
