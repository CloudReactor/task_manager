import { Task } from '../../types/domain_types';
import * as C from '../../utils/constants'

import React, { Fragment, useContext, useState } from "react";
import {
  TextField,
  Radio,
  FormControl,
  FormControlLabel,
  RadioGroup
} from '@material-ui/core';

import { Alert } from 'react-bootstrap';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import ActionButton from '../common/ActionButton';
import "./styles.scss";

interface Props {
  task: Task;
  editTask: (uuid: string, data: any) => Promise<void>;
  handleClose: () => void;
}

const TASK_SCHEDULE_TYPE_SCHEDULED = 'scheduled';
const TASK_SCHEDULE_TYPE_ON_DEMAND = 'on-demand';
const TASK_TYPE_SERVICE = 'service';

const ConfigModalBody = ({
  task,
  editTask,
  handleClose
}: Props) => {
  const context = useContext(GlobalContext);
  const accessLevel = accessLevelForCurrentGroup(context);
  const isMutationAllowed = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  const awscron = "cron(<minute> <hour> <day-of-month> <month> <day-of-week> <year>)";
  const awsrate = "rate(<value> <unit>)"
  const [schedule, setSchedule] = useState(task.schedule);
  const [serviceInstanceCount, setServiceInstanceCount] = useState(task.service_instance_count);
  const initialTaskScheduleType = task.is_service ? TASK_TYPE_SERVICE :
      (task.schedule ? TASK_SCHEDULE_TYPE_SCHEDULED : TASK_SCHEDULE_TYPE_ON_DEMAND);
  const [taskScheduleType, setTaskScheduleType] = useState(initialTaskScheduleType);
  const focusScheduleInput = (input: any) => {
    input && input.focus();
  };
  const [saveErrorMessage, setSaveErrorMessage] = useState('');
  const [saveInProgress, setSaveInProgress] = useState(false);
  const serviceInputProps = { min: 1 };

  function handleChange(event: React.ChangeEvent<unknown>) {
    setTaskScheduleType((event.target as HTMLInputElement).value);
  }

  function saveConfig() {
    const data: any = {};

    if (taskScheduleType === TASK_SCHEDULE_TYPE_SCHEDULED) {
      data.is_service = false
      data.schedule = schedule;
      data.service_instance_count = null;
      data.min_service_instance_count = null;
    } else if (taskScheduleType === TASK_TYPE_SERVICE) {
      data.is_service = true;
      data.schedule = ''
      data.service_instance_count = serviceInstanceCount || 1;
      data.min_service_instance_count = data.service_instance_count;
    } else {
      data.is_service = false;
      data.schedule = ''
      data.service_instance_count = null;
      data.min_service_instance_count = null;
    }

    setSaveInProgress(true);

    editTask(task.uuid, data).then(() => {
        setSaveErrorMessage('');
        handleClose();
        setSaveInProgress(false);
    }, (err: Error) => {
        console.dir(err);
        setSaveErrorMessage(err.message ||
          'An error saving occurred. Please try again later.')
        setSaveInProgress(false);
    });
  }

  return (
    <div className="container pb-2 px-4">
      {
        saveErrorMessage &&
        <Alert variant="danger">
          { saveErrorMessage }
        </Alert>
      }

      <div className="config-modal-section">
        <p className="config-modal-section-title">Change Task Schedule:</p>
        <div>
          <FormControl component="fieldset" disabled={!isMutationAllowed} >
            <RadioGroup aria-label="Task Schedule" name="process_schedule"
             value={taskScheduleType} onChange={handleChange} >
              <FormControlLabel value={TASK_SCHEDULE_TYPE_ON_DEMAND} control={<Radio color="primary" />} label="On-demand" />
              <FormControlLabel value={TASK_SCHEDULE_TYPE_SCHEDULED} control={<Radio color="primary" />} label="Scheduled" />
              {
                (taskScheduleType === TASK_SCHEDULE_TYPE_SCHEDULED) &&
                <Fragment>
                  <TextField
                    id="schedule"
                    autoFocus={true}
                    inputRef={focusScheduleInput}
                    disabled={!isMutationAllowed || (taskScheduleType !== TASK_SCHEDULE_TYPE_SCHEDULED)}
                    defaultValue={schedule}
                    fullWidth={true}
                    label="Enter schedule expression"
                    type="string"
                    name="schedule"
                    margin="dense"
                    variant="outlined"
                    onChange={event => setSchedule(event.target.value)}
                  />
                  <p className="pt-3">
                    Schedule expressions must be an AWS &nbsp;
                    <a
                      className="link"
                      href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html"
                      target="_blank"
                      rel="noopener noreferrer"
                    >cron or rate expression
                    </a>.
                  </p>
                  <div id="cron-help">
                    <p>
                      <span className="font-weight-bold">{"cron syntax: "}</span>
                      <span className="text-monospace">{awscron}</span>
                    </p>
                    <div className="row">
                      <div className="col">
                      </div>
                      <div className="col-11">
                        <div>E.g. run at noon UTC every day:</div>
                        <div className="border border-light bg-dark rounded text-monospace p-2 m-2">
                          cron(0 12 * * ? *)
                        </div>
                        <div>E.g. run at 9.15pm UTC Mon-Fri:</div>
                        <div className="border border-light bg-dark rounded text-monospace p-2 m-2">
                          cron(15 21 ? * MON-FRI *)
                        </div>
                      </div>
                    </div>
                    <div className="mt-3">
                      <span className="font-weight-bold">{"rate syntax: "}</span>
                      <span className="text-monospace">{awsrate}</span>
                    </div>
                    <div className="row">
                      <div className="col">
                      </div>
                      <div className="col-11">
                        <div>e.g. run every 6 hours:</div>
                        <div className="border border-light bg-dark rounded text-monospace p-2 m-2">
                          rate(6 hours)
                        </div>
                      </div>
                    </div>
                  </div>
                </Fragment>
              }
              <FormControlLabel value={TASK_TYPE_SERVICE} control={<Radio color="primary" />} label="Service" />
              {
                (taskScheduleType === TASK_TYPE_SERVICE) &&
                <Fragment>
                  <TextField
                    inputProps={serviceInputProps}
                    id="service_instance_count"
                    autoFocus={true}
                    inputRef={focusScheduleInput}
                    disabled={!isMutationAllowed || (taskScheduleType !== TASK_TYPE_SERVICE)}
                    defaultValue={serviceInstanceCount || 1}
                    fullWidth={true}
                    label="Desired instance count"
                    type="number"
                    name="service_instance_count"
                    margin="dense"
                    variant="outlined"
                    onChange={event => setServiceInstanceCount(parseInt(event.target.value))}
                  />
                </Fragment>
              }
            </RadioGroup>
          </FormControl>
        </div>
      </div>

      <div className="d-flex justify-content-end mt-2">
        {
          isMutationAllowed && (
            <ActionButton
              action="save"
              label="Save"
              inProgress={saveInProgress}
              inProgressLabel="Saving"
              onActionRequested={(action, cbData) => saveConfig()}
              size="medium"
              color="primary"
              variant="contained"
            />
          )
        }
        <ActionButton
          action="cancel"
          label={isMutationAllowed ? 'Cancel' : 'Close'}
          onActionRequested={(action, cbData) => handleClose()}
          size="medium"
          color="default"
          variant="contained"
        />
      </div>

    </div>
  );
};

export default ConfigModalBody;
