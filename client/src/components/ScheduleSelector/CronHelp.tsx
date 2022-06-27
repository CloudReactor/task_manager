import React from 'react';
import styles from './CronHelp.module.scss';

const CronHelp = () => {
  const awscron = "cron(<minute> <hour> <day-of-month> <month> <day-of-week> <year>)";
  const awsrate = "rate(<value> <unit>)"
  
  return (
    <div id="cron-help" className={styles.cronHelp}>
      <p className="pt-3">
        Note: schedule expressions must be an AWS &nbsp;
        <a
          className="link"
          href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html"
          target="_blank"
          rel="noopener noreferrer"
        >cron or rate expression
        </a>.
      </p>
      <p className="font-weight-bold">
        Cron syntax:
      </p>
      <p className="text-monospace">
        {awscron}
      </p>
      <div className="row">
        <div className="col">
        </div>
        <div className="col-11">
          <div>E.g. Noon UTC every day:</div>
          <div className="form-control my-2">
            cron(0 12 * * ? *)
          </div>
          <div>E.g. 9.55pm UTC Mon-Fri:</div>
          <div className="form-control my-2">
            cron(55 21 ? * MON-FRI *)
          </div>
        </div>
      </div>
      <p className="font-weight-bold">
        Rate syntax:
      </p>
      <p className="text-monospace">
        {awsrate}
      </p>
      <div className="row">
        <div className="col">
        </div>
        <div className="col-11">
          <div>e.g. run every 6 hours:</div>
          <div className="form-control my-2">
            rate(6 hours)
          </div>
        </div>
      </div>
    </div>
  );
}

export default CronHelp;