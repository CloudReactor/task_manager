import moment from "moment";
import React, { Fragment } from "react";
import { isCancel } from 'axios';
import { withRouter } from 'react-router';
import Chart from "../../../components/Chart/Chart";
import { fetchWorkflowExecutionSummaries } from "../../../utils/api";
import { timeFormat } from "../../../utils/index";
import { WORKFLOW_EXECUTION_STATUS_SUCCEEDED } from "../../../utils/constants";
import cancelTokenHoc, { CancelTokenProps } from '../../../hocs/cancelTokenHoc';
import * as UIC from '../../../utils/ui_constants';

interface Props {
  uuid: string;
  history: any;
}

interface State {
  data: any[] | null;
  interval: any;
}

type InnerProps = Props & CancelTokenProps;

const extractChartValues = (filteredData: any[], extractY: (execution: any) => string) => {
  const labels: string[] = [];
  const dataset: string[] = [];
  const colors: string[] = [];
  const borderColors: string[] = [];


  filteredData.forEach((item: { status: string, started_at: Date; finished_at: Date }) => {
    labels.push(timeFormat(item.started_at));
    dataset.push(extractY(item));

    if (item.status === WORKFLOW_EXECUTION_STATUS_SUCCEEDED) {
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


class Charts extends React.Component<InnerProps, State> {
  constructor(props: InnerProps) {
    super(props);

    this.state = {
      data: null,
      interval: null
    };
  }

  loadWorkflowExecutions = async () => {
    try {
      const workflowExecutionsData = await fetchWorkflowExecutionSummaries(
        this.props.uuid,
        'started_at',
        true,
        undefined,
        undefined,
        this.props.cancelToken,
      );
      this.setState({
        data: workflowExecutionsData.results.reverse()
      });
    } catch (error) {
      if (isCancel(error)) {
        console.log('Request cancelled: ' + error.message);
        return;
      } else {
        console.log(error);
      }
    }
  }

  async componentDidMount() {
    await this.loadWorkflowExecutions();

    const interval = setInterval(this.loadWorkflowExecutions,
      UIC.TASK_REFRESH_INTERVAL_MILLIS);

    this.setState({
      interval
    });
  }

  componentWillUnmount() {
    if (this.state.interval) {
      clearInterval(this.state.interval);
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

      const onClick = (event: any, chartElements: any[]) => {
        console.log('event:');
        console.dir(event);

        console.log('chartElements:');
        console.dir(chartElements);

        if (chartElements.length === 1) {
          const execution = filteredData[chartElements[0]._index];
          history.push(`/workflow_executions/${execution.uuid}`);
        }
      }

      return (
        <Fragment>
          <div className="row pt-4">
            <div className="col-lg-12">
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
          </div>
        </Fragment>
      );
    }
    return null;
  }
}
export default withRouter(cancelTokenHoc(Charts));