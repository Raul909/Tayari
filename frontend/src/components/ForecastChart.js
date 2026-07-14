'use client';

import { useRef, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

export default function ForecastChart({ discharge }) {
  if (!discharge || !discharge.data || discharge.data.length === 0) {
    return (
      <div className="loading-container">
        <span>No discharge data available</span>
      </div>
    );
  }

  const labels = discharge.data.map((d) => {
    const date = new Date(d.date);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  });

  const dischargeMean = discharge.data.map((d) => d.discharge_mean);
  const dischargeMax = discharge.data.map((d) => d.discharge_max);
  const dischargeMin = discharge.data.map((d) => d.discharge_min);

  // Find today's index
  const today = new Date().toISOString().slice(0, 10);
  const todayIdx = discharge.data.findIndex((d) => d.date === today);

  const data = {
    labels,
    datasets: [
      // Uncertainty band (max-min)
      {
        label: 'Max',
        data: dischargeMax,
        borderColor: 'transparent',
        backgroundColor: 'rgba(59, 130, 246, 0.08)',
        fill: '+1',
        pointRadius: 0,
        tension: 0.3,
      },
      {
        label: 'Min',
        data: dischargeMin,
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        fill: false,
        pointRadius: 0,
        tension: 0.3,
      },
      // Mean discharge line
      {
        label: 'Discharge (m³/s)',
        data: dischargeMean,
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2.5,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: '#3B82F6',
        tension: 0.3,
      },
      // Flood threshold line
      {
        label: 'Flood Threshold',
        data: Array(labels.length).fill(discharge.flood_threshold),
        borderColor: '#EF4444',
        borderWidth: 1.5,
        borderDash: [6, 4],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0,
      },
      // Warning threshold line
      {
        label: 'Warning Level',
        data: Array(labels.length).fill(discharge.warning_threshold),
        borderColor: '#EAB308',
        borderWidth: 1,
        borderDash: [4, 4],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 1.8,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          color: '#94A3B8',
          font: { size: 10, family: 'Inter' },
          boxWidth: 12,
          padding: 10,
          filter: (item) => !['Max', 'Min'].includes(item.text),
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 29, 50, 0.95)',
        titleColor: '#F0F4F8',
        bodyColor: '#94A3B8',
        borderColor: 'rgba(148, 163, 184, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
        padding: 10,
        titleFont: { family: 'Inter', weight: '600' },
        bodyFont: { family: 'Roboto Mono', size: 12 },
        callbacks: {
          label: (ctx) => {
            if (['Max', 'Min'].includes(ctx.dataset.label)) return null;
            return `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(1)} m³/s`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(148, 163, 184, 0.06)' },
        ticks: {
          color: '#64748B',
          font: { size: 10, family: 'Inter' },
          maxRotation: 45,
          maxTicksLimit: 8,
        },
      },
      y: {
        grid: { color: 'rgba(148, 163, 184, 0.06)' },
        ticks: {
          color: '#64748B',
          font: { size: 10, family: 'Roboto Mono' },
        },
        title: {
          display: true,
          text: 'm³/s',
          color: '#64748B',
          font: { size: 10 },
        },
      },
    },
  };

  return <Line data={data} options={options} />;
}
