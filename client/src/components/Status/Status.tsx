import React from 'react';
import { displayStatus } from "../../utils/index";
import * as C from '../../utils/constants';
import styles from './Status.module.scss';

interface Props {
  enabled: boolean;
	status: string;
	isService: boolean;
	forExecutionDetail: boolean;
}

const Status = ({enabled, status, isService, forExecutionDetail}: Props) => {
	const statusLabel = displayStatus(enabled, status, isService, forExecutionDetail);

	let icon;
	if (status === C.TASK_EXECUTION_STATUS_SUCCEEDED && !isService) {
    icon = <i className="fas fa-check"></i>;
	} else if (statusLabel === 'Up') {
		icon = <i className="fas fa-check"></i>;
  } else if ((C.TASK_EXECUTION_STATUSES_WITH_PROBLEMS.indexOf(status) >= 0) ||
						 (enabled && (statusLabel === 'DOWN'))) {
    icon = <i className="fas fa-exclamation-triangle"></i>;
  } else if (status === C.TASK_EXECUTION_STATUS_RUNNING) {
		icon = 	<i className="fas fa-spinner fa-spin"></i>;
	} else if (status === C.TASK_EXECUTION_STATUS_MANUALLY_STARTED ||
			       status === C.TASK_EXECUTION_STATUS_STOPPING) {
		icon = <i className="fas fa-circle-notch fa-spin"></i>
	}

	return(
		<div className={styles.taskStatus}>
			{icon}
			<span>{statusLabel}</span>
		</div>
	);
}

export default Status;