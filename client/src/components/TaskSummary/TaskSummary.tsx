import { Task } from "../../types/domain_types";

import React from 'react';
import { Link } from "react-router-dom";

import { Button } from 'react-bootstrap'
import CopyToClipboard from 'react-copy-to-clipboard';

import styles from './TaskSummary.module.scss';

function createData(name: string, data: any, isUrl: boolean = false,
    urlLabel: string = '', addCopyButton: boolean = false) {
  return { name, data, isUrl, urlLabel, addCopyButton };
}

interface Props {
  task: Task;
}

const TaskSummary = ({ task }: Props) => {
  const scheduleText = task.is_service ? "Service (always-on)"
    : (task.schedule || 'On-demand');

  const rows = [
    createData('Description', task.description ?? 'N/A'),
    createData('Task Type', scheduleText),
    createData('Run Environment',
        <Link to={'/run_environments/' + encodeURIComponent(task.run_environment.uuid)}>{task.run_environment.name}</Link>)
  ];

  if (task.project_url) {
    rows.push(createData('Project URL', task.project_url, true));
  }

  if (task.logs_url) {
    // TODO: add clipboad copy button
    rows.push(createData('Log query', task.logs_url, true, task.log_query, true));
  }

  return (
    <div className={styles.summaryContainer}>
      {
        rows.map((row, index) => {
          if (row.name === 'Description') {
            return (<div key={index} className={styles.description}>{row.data}</div>);
          } else {
            return(
              <div key={index}>{row.name}:{' '}
                {
                  (row.isUrl && row.data) ? (
                      /^https?:\/\//.test(row.data.toString())
                      ? <a href={row.data} target="_blank" rel="noopener noreferrer">{row.urlLabel || row.data}</a>
                      : <Link to={row.data}>{row.urlLabel || row.data}</Link>
                  ) : row.data
                }
                {
                  row.addCopyButton && (
                    <CopyToClipboard text={row.urlLabel || row.data}>
                      <Button size="sm" variant="outline-secondary"
                       className={styles.copyButton}>
                        <i className="fas fa-clipboard"/>
                      </Button>
                    </CopyToClipboard>
                  )
                }


              </div>
            );
          }
        }
      )}
    </div>
  );
}


export default TaskSummary;
