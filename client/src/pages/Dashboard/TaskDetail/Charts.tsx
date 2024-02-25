import moment from 'moment';

import * as path from '../../../constants/routes';

import React, { Component, Fragment } from 'react';
import Chart from '../../../components/Chart/Chart';

import * as C from '../../../utils/constants';
import { timeFormat } from '../../../utils/index';
import { fetchTaskExecutions } from '../../../utils/api';
import { TaskExecution, TaskImpl } from '../../../types/domain_types';

interface Props {
  task: TaskImpl;
  history: any;
}

interface State {
  taskExecutions: TaskExecution[] | null;
}

const extractChartValues = (filteredData: TaskExecution[], extractY: (execution: TaskExecution) => string) => {
  const labels: string[] = [];
  const dataset: string[] = [];
  const colors: string[] = [];
  const borderColors: string[] = [];

  filteredData.forEach(execution => {
    labels.push(timeFormat(execution.started_at));
    dataset.push(extractY(execution));

    if (execution.status === C.TASK_EXECUTION_STATUS_SUCCEEDED) {
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

export default class Charts extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
      taskExecutions: null
    };
  }

  async componentDidMount() {
    try {
      const taskExecutionPage = await fetchTaskExecutions({
        taskUuid: this.props.task.uuid,
        sortBy: '-started_at'
      });

      this.setState({
        taskExecutions: taskExecutionPage.results.reverse()
      });
    } catch (error) {
      console.log('Error fetching Task Executions');
    }
  }

  render() {
    const {
      history
    } = this.props;

    const { taskExecutions } = this.state;
    if (taskExecutions) {
      const finishedExecutions = taskExecutions.filter(taskExecution =>
        !!taskExecution.finished_at
      );

      const runDurations = extractChartValues(finishedExecutions, (execution) => {
        return moment(execution.finished_at)
          .diff(moment(execution.started_at), "minutes", true).toFixed(1)
      });

      let anyProcessedCounts = false;
      const processedCounts = extractChartValues(taskExecutions, (execution) => {
        if (execution.success_count) {
          anyProcessedCounts = true;
        }

        return (execution.success_count || 0).toString();
      });

      const onClick = (event: any, chartElements: any[]) => {
        console.log('event:');
        console.dir(event);

        console.log('chartElements:');
        console.dir(chartElements);

        if (chartElements.length === 1) {
          const execution = finishedExecutions[chartElements[0].index];
          history.push(path.TASK_EXECUTIONS + '/' + execution.uuid);
        }
      }

      const runDurationWidth = 50 * (anyProcessedCounts ? 1 : 2);
      const runDurationClass = 'col-lg-' + (6 * (anyProcessedCounts ? 1 : 2)).toString() +
        ' col-md-12';

      return (
        <Fragment>
          <div className="row pt-4">
            <div className={runDurationClass}>
              <Chart
                labels={runDurations.labels}
                data={runDurations.dataset}
                width={runDurationWidth}
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
            {
              anyProcessedCounts && (
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
              )
            }
            </div>
          </div>
        </Fragment>
      );
    }
    return null;
  }
}
