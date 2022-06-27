import React from 'react';
import { Link } from "react-router-dom";
import { Task } from "../../types/domain_types";
import styles from './TaskSummary.module.scss';

function createData(name: string, data: any, isUrl: boolean = false, urlLabel: string = '') {
  return { name, data, isUrl, urlLabel };
}

interface Props {
  task: Task;
}

const TaskSummary = ({ task }: Props) => {
  const scheduleText = task.is_service ? "Service (always-on)"
    : (task.schedule || 'On-demand');

  const rows = [
    createData('Description', task.description ?? 'N/A'),
    createData('Schedule', scheduleText),
    createData('Run environment',
        <Link to={'/run_environments/' + encodeURIComponent(task.run_environment.uuid)}>{task.run_environment.name}</Link>)
  ];

  if (task.project_url) {
    rows.push(createData('Project URL', task.project_url, true));
  }

  if (task.logs_url) {
    rows.push(createData('Log query', task.logs_url, true, task.log_query));
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
              </div>
            );
          }
        }
      )}
    </div>
  );
}


export default TaskSummary;
