import moment from 'moment';

import * as path from '../../../constants/routes';

import React, { Fragment } from 'react';
import Chart from '../../../components/Chart/Chart';
import { timeFormat } from '../../../utils/index';
import { fetchTaskExecutions } from '../../../utils/api';

interface Props {
  id: string;
  history: any;
}

interface State {
  data: any[] | null;
}

const extractChartValues = (filteredData: any[], extractY: (execution: any) => string) => {
  const labels: string[] = [];
  const dataset: string[] = [];
  const colors: string[] = [];
  const borderColors: string[] = [];

  filteredData.forEach((item: { status: string, started_at: Date; finished_at: Date }) => {
    labels.push(timeFormat(item.started_at));
    dataset.push(extractY(item));

    if (item.status === 'SUCCEEDED') {
      colors.push('#1ad61a91');
      borderColors.push('green');
    } else {
      colors.push('rgba(255,99,132,0.2)');
      borderColors.push('rgba(255,99,132,1)');
    }
  });

  return {
    labels,
    dataset,
    colors,
    borderColors
  };
};

export default class Charts extends React.Component<Props, State> {
  constructor(props: any) {
    super(props);

    this.state = {
      data: null
    };
  }

  async componentDidMount() {
    try {
      const taskExecutionPage = await fetchTaskExecutions({
        taskUuid: this.props.id,
        sortBy: '-started_at'
      });

      this.setState({
        data: taskExecutionPage.results.reverse()
      });
    } catch (error) {
      console.log('Error fetching Task Executions');
    }
  }

  render() {
    const {
      history
    } = this.props;

    const {data} = this.state;
    if (data) {
      const filteredData = data.filter((item: {status: string, finished_at: Date}) => {
        return item.finished_at;
      });

      const runDurations = extractChartValues(filteredData, (execution: any) => {
        return moment(execution.finished_at)
          .diff(moment(execution.started_at), "minutes", true).toFixed(1)
      });

      const processedCounts = extractChartValues(filteredData, (execution: any) => {
        return (execution.success_count || 0).toString();
      });

      const onClick = (event: any, chartElements: any[]) => {
        console.log('event:');
        console.dir(event);

        console.log('chartElements:');
        console.dir(chartElements);

        if (chartElements.length === 1) {
          const execution = filteredData[chartElements[0]._index];
          history.push(path.TASK_EXECUTIONS + '/' + execution.uuid);
        }
      }

      return (
        <Fragment>
          <div className="row pt-4">
            <div className="col-lg-6 col-md-12">
              <Chart
                labels={runDurations.labels}
                data={runDurations.dataset}
                width={50}
                graphName="Run duration (mins)"
                colors={runDurations.colors}
                borderColors={runDurations.borderColors|| runDurations.colors}
                hoverBackgroundColor="#1ad61a91"
                hoverBorderColor="#1ad61a91"
                noDataMessage='No executions have completed yet.'
                onClick={onClick}
              />
            </div>
            <div className="col-lg-6 col-md-12">
              <Chart
                labels={processedCounts.labels}
                data={processedCounts.dataset}
                width={50}
                graphName="Processed count"
                colors={processedCounts.colors}
                borderColors={processedCounts.borderColors}
                hoverBackgroundColor="#1ad61a91"
                hoverBorderColor="#1ad61a91"
                noDataMessage='No executions have completed yet.'
                onClick={onClick}
              />
            </div>
          </div>
        </Fragment>
      );
    }
    return null;
  }
}
