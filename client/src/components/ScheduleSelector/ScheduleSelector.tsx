import * as C from '../../utils/constants';
import { Workflow } from '../../types/domain_types';

import React, { useContext, useState } from "react";
import { Field, FormikProps } from 'formik';

import {
  accessLevelForCurrentGroup,
  GlobalContext
} from '../../context/GlobalContext';

import CronHelp from './CronHelp';
import CustomButton from '../common/Button/CustomButton';
import CustomInput from '../forms/CustomInput';
import styles from './ScheduleSelector.module.scss';

interface Props {
  workflow: Workflow;
  formikProps: FormikProps<Workflow>;
}

const SCHEDULE_TYPE_SCHEDULED = 'scheduled';
const SCHEDULE_TYPE_ON_DEMAND = 'on-demand';

const ScheduleSelector = ({
  workflow,
  formikProps,
}: Props) => {
  const { isSubmitting, setFieldValue, handleChange, submitForm } = formikProps;

  const context = useContext(GlobalContext);
  const accessLevel = accessLevelForCurrentGroup(context);
  const initialScheduleType = workflow.schedule ? SCHEDULE_TYPE_SCHEDULED : SCHEDULE_TYPE_ON_DEMAND;
  const [scheduleType, setScheduleType] = useState(initialScheduleType);

  if (!accessLevel) {
    return null;
  }
  const canSave = (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

  function changeProcessSchedule(event: React.ChangeEvent<unknown>) {
    const scheduleType = (event.target as HTMLInputElement).value;
    setScheduleType(scheduleType);
  }

  function handleSubmit() {
    if (scheduleType !== SCHEDULE_TYPE_SCHEDULED) {
      setFieldValue('schedule', '');
    }

    submitForm();
  }

  return (
    <div className={styles.formContainer}>
      <fieldset disabled={!canSave}>
        <div className={styles.formSection}>
          <div role="group" aria-label="Process Schedule">
            <CustomInput
              field={{
                name: "process_schedule",
                value: SCHEDULE_TYPE_ON_DEMAND
              }}
              type="radio"
              label="On-demand"
              checked={scheduleType === SCHEDULE_TYPE_ON_DEMAND}
              onChange={changeProcessSchedule}
            />
            <CustomInput
              field = {{
                name: "process_schedule",
                value: SCHEDULE_TYPE_SCHEDULED
              }}
              type="radio"
              label="Scheduled"
              checked={scheduleType === SCHEDULE_TYPE_SCHEDULED}
              onChange={changeProcessSchedule}
            />
          </div>
          <Field
            name="schedule"
            type="text"
            label="Enter schedule expression"
            placeholder="e.g. cron(0 14 * * ? *)"
            component={CustomInput}
            disabled={scheduleType !== SCHEDULE_TYPE_SCHEDULED}
            subText="Enter an AWS cron or rate expression"
            onChange={handleChange}
          />
          {
            canSave && (
              <CustomButton
                color="primary"
                type="button"
                disabled={isSubmitting}
                label="Save changes"
                inProgress={isSubmitting}
                faIconName="save"
                onActionRequested={(action, cbData) => handleSubmit()}
              />
            )
          }
          <CronHelp />
        </div>
      </fieldset>
    </div>
  );
};

export default ScheduleSelector;