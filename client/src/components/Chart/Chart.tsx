import React, { memo } from "react";
import { Bar } from "react-chartjs-2";
import { Typography } from '@mui/material';
import styles from './Chart.module.scss';

interface Props {
  labels: string[];
  data: number[] | string[];
  colors?: string[],
  graphName: string;
  width?: number;
  height?: number;
  backgroundColor?: string;
  borderColor?: string;
  borderColors?: string[],
  borderWidth?: number;
  hoverBackgroundColor?: string;
  hoverBorderColor?: string;
  noDataMessage?: string;
  onClick?: (event: any, chartElements: any[]) => void;
}

const Chart = memo(
  ({
    graphName,
    labels,
    data,
    colors,
    width,
    height,
    backgroundColor,
    borderColor,
    borderColors,
    hoverBackgroundColor,
    hoverBorderColor,
    noDataMessage,
    onClick
  }: Props) =>
    data.length ? (
      <div className={styles.chartContainer}>
        <Typography variant="subtitle1" align="center">
          {graphName}
        </Typography>
        <Bar
          data={{
            labels,
            datasets: [
              {
                backgroundColor: colors || backgroundColor,
                borderColor: borderColors || borderColor,
                borderWidth: 1,
                hoverBackgroundColor: colors || hoverBackgroundColor,
                hoverBorderColor: borderColors || hoverBorderColor,
                data
              }
            ]
          }}
          width={width || 100}
          height={height || 100}
          options={{
            plugins: {
              legend: {
                display: false
              },
            },
            scales: {
              y: {
                beginAtZero: true,
              }
            },
            maintainAspectRatio: false,
            onClick
          }}
        />
      </div>
    ) : (
       <div className="no-data">
         <div className="graph-name">{graphName}</div>
         <div className="message">{noDataMessage}</div>
       </div>
    )
);

Chart.displayName = 'Chart';

export default Chart;