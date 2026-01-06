import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import React, { lazy, useContext, Suspense } from 'react';
import {
  Route,
  Routes
} from 'react-router-dom';

import {
  Container
} from 'react-bootstrap/'

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import * as path from '../../constants/routes';
import isAuth from '../../hocs/index';

import NavBar from '../../components/NavBar';
import Loading from '../../components/Loading';
import UTCTimeMemo from "../../components/common/UTCTimeMemo";
import styles from './index.module.scss';

const WorkflowList = lazy(() =>
  import('./WorkflowList')
);

const WorkflowDetail = lazy(() =>
  import('./WorkflowDetail')
);

const WorkflowExecutionDetail = lazy(() =>
  import('./WorkflowExecutionDetail')
);

const TaskList = lazy(() => import('./TaskList'));
const TaskDetail = lazy(() =>
  import('./TaskDetail')
);
const TaskExecutionDetail = lazy(() =>
  import('./TaskExecutionDetail')
);

const RunEnvironmentList = lazy(() =>
  import('./RunEnvironment')
);

const RunEnvironmentDetail = lazy(() =>
  import('./RunEnvironmentDetail')
);

const GroupList = lazy(() =>
  import('./Group')
);

const GroupEditor = lazy(() =>
  import('./Group/GroupEditor')
);

const ApiKeyList = lazy(() =>
  import('./ApiKey')
);

const ApiKeyEditor = lazy(() =>
  import('./ApiKey/ApiKeyEditor')
);

const Profile = lazy(() =>
  import('./Profile/ProfileEditor')
);

const EmailNotificationProfileList = lazy(() =>
  import('./EmailNotificationProfile')
);

const EmailNotificationProfileDetail = lazy(() =>
  import('./EmailNotificationProfileDetail')
);

const PagerDutyProfileList = lazy(() =>
  import('./PagerDutyProfile')
);

const PagerDutyProfileDetail = lazy(() =>
  import('./PagerDutyProfileDetail')
);

const NotificationMethodList = lazy(() =>
  import('./NotificationMethod')
);

const NotificationMethodDetail = lazy(() =>
  import('./NotificationMethodDetail')
);

const NotificationDeliveryMethodList = lazy(() =>
  import('./NotificationDeliveryMethod')
);

const NotificationDeliveryMethodDetail = lazy(() =>
  import('./NotificationDeliveryMethodDetail')
);

type Props = Record<string, never>;

const Dashboard = (p: Props) => {
  const context = useContext(GlobalContext);

  const {
    currentGroup
  } = context;

  if (!currentGroup) {
    return <Loading />;
  }

  const accessLevel = accessLevelForCurrentGroup(context);
  const hasDeveloperAccess = accessLevel && (accessLevel >= ACCESS_LEVEL_DEVELOPER);

  return (
    <div className={styles.dashboardContainer}>
      <NavBar />
      <main className={styles.dashboardContent}>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path={path.DASHBOARD} element={ <TaskList /> } />
            <Route path={path.WORKFLOWS} element={ <WorkflowList /> } />
            <Route path={path.WORKFLOW} element={ <WorkflowDetail /> } />
            <Route path={path.WORKFLOW_EXECUTION} element={ <WorkflowExecutionDetail /> } />
            <Route path={path.TASK} element={ <TaskDetail /> } />
            <Route path={path.TASK_EXECUTION} element={ <TaskExecutionDetail /> } />
            <Route path={path.RUN_ENVIRONMENTS} element={ <RunEnvironmentList /> } />
            <Route path={path.RUN_ENVIRONMENT} element={ <RunEnvironmentDetail /> } />
            <Route path={path.GROUPS} element={ <GroupList /> } />
            <Route path={path.GROUP} element={ <GroupEditor /> } />
            <Route path={path.EMAIL_NOTIFICATION_PROFILES} element={ <EmailNotificationProfileList /> } />
            <Route path={path.EMAIL_NOTIFICATION_PROFILE} element={ <EmailNotificationProfileDetail /> } />
            <Route path={path.PAGERDUTY_PROFILES} element={ <PagerDutyProfileList /> } />
            <Route path={path.PAGERDUTY_PROFILE} element={ <PagerDutyProfileDetail /> } />
            <Route path={path.NOTIFICATION_METHODS} element={ <NotificationMethodList /> } />
            <Route path={path.NOTIFICATION_METHOD} element={ <NotificationMethodDetail /> } />
            <Route path={path.NOTIFICATION_DELIVERY_METHODS} element={ <NotificationDeliveryMethodList /> } />
            <Route path={path.NOTIFICATION_DELIVERY_METHOD} element={ <NotificationDeliveryMethodDetail /> } />
            {
              hasDeveloperAccess && (
                <Route path={path.API_KEYS}
                 element={ <ApiKeyList /> } />
              )
            }
            {
              hasDeveloperAccess && (
                <Route path={path.API_KEY} element={ <ApiKeyEditor /> } />
              )
            }
            <Route path={path.PROFILE} element={ <Profile /> } />
            <Route path="*" element = {
              <Container className="ml-0">
                <h1>Page Not Found</h1>
                <p>
                  This page was not found or you do not have permission to access the page.
                </p>
              </Container>
            } />
          </Routes>
        </Suspense>
      </main>
      <div className={styles.dashboardFooter}>
        <UTCTimeMemo />
        {
          (import.meta.env.VITE_DEPLOYMENT !== 'production') &&
          <p>Version {import.meta.env.VITE_VERSION_SIGNATURE}</p>
        }
      </div>
    </div>
  );
}

export default isAuth(Dashboard);
