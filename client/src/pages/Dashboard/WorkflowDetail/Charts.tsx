import moment from "moment";

import {
  WorkflowExecutionSummary
} from '../../../types/domain_types';

import {
  fetchWorkflowExecutionSummaries
} from "../../../utils/api";

import { timeFormat } from "../../../utils/index";
import { WORKFLOW_EXECUTION_STATUS_SUCCEEDED } from "../../../utils/constants";


import React, { Fragment, useEffect, useState } from "react";
import { useNavigate } from 'react-router-dom';
import { isCancel } from 'axios';

import Chart from "../../../components/Chart/Chart";
import * as UIC from '../../../utils/ui_constants';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';


interface Props {
  uuid: string;
  executionCount?: number;
}

const DEFAULT_EXECUTION_COUNT = 25;

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


const Charts = (props: Props & AbortSignalProps) => {
  const {
    executionCount,
    abortSignal,
    uuid
  } = props;

  const [weSummaries, setWeSummaries] = useState<Array<WorkflowExecutionSummary> | null>(null);
  const [selfInterval, setSelfInterval] = useState<any>(null);

  const loadWorkflowExecutions = async () => {
    try {
      const workflowExecutionsData = await fetchWorkflowExecutionSummaries({
        workflowUuid: uuid,
        sortBy: 'started_at',
        descending: true,
        offset: 0,
        maxResults: executionCount ?? DEFAULT_EXECUTION_COUNT,
        abortSignal
      });
      setWeSummaries(workflowExecutionsData.results.reverse());
    } catch (error) {
      if (!isCancel(error)) {
        console.log(error);
        throw error;
      }
    }
  }

  useEffect(() => {
    if (weSummaries === null) {
      loadWorkflowExecutions();
    }

    if (!selfInterval) {
      const interval = setInterval(loadWorkflowExecutions,
        UIC.TASK_REFRESH_INTERVAL_MILLIS);
      setSelfInterval(interval);
    }

    return () => {
      if (selfInterval) {
        clearInterval(selfInterval);
      }
    };
  }, []);

  const navigate = useNavigate();

  if (weSummaries) {
    const filteredData = weSummaries.filter((item: {status: string, finished_at: Date}) => {
      return item.finished_at;
    });

    const runDurations = extractChartValues(filteredData, (execution: any) => {
      return moment(execution.finished_at)
        .diff(moment(execution.started_at), "minutes", true).toFixed(1)
    });

    const onClick = (event: any, chartElements: any[]) => {
      if (chartElements.length === 1) {
        const execution = filteredData[chartElements[0]._index];
        navigate(`/workflow_executions/${execution.uuid}`);
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
              graphName="Run duration (minutes)"
              colors={runDurations.colors}
              borderColors={runDurations.borderColors|| runDurations.colors}
              hoverBackgroundColor="#1ad61a91"
              hoverBorderColor="#1ad61a91"
              noDataMessage='No Workflow Executions have completed yet.'
              onClick={onClick}
            />
          </div>
        </div>
      </Fragment>
    );
  }
  return null;
}
export default abortableHoc(Charts);
