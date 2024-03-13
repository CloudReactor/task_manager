import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import React, { lazy, useContext, Suspense } from 'react';
import {
  Route,
  Switch
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
          <Switch>
            <Route
              exact
              path={path.DASHBOARD}
            >
              <TaskList />
            </Route>
            <Route
              exact
              path={path.WORKFLOWS}
            >
              <WorkflowList />
            </Route>
            <Route
              exact
              path={path.WORKFLOW}
            >
              <WorkflowDetail />
            </Route>
            <Route
              exact
              path={path.WORKFLOW_EXECUTION}
            >
              <WorkflowExecutionDetail />
            </Route>
            <Route
              exact
              path={path.TASK}
            >
              <TaskDetail />
            </Route>
            <Route
              exact
              path={path.TASK_EXECUTION}
            >
              <TaskExecutionDetail />
            </Route>
            <Route
              exact
              path={path.RUN_ENVIRONMENTS}
            >
              <RunEnvironmentList />
            </Route>
            <Route
              exact
              path={path.RUN_ENVIRONMENT}
            >
              <RunEnvironmentDetail />
            </Route>
            <Route exact path={path.GROUPS}>
              <GroupList />
            </Route>
            <Route
              exact
              path={path.GROUP}
            >
              <GroupEditor />
            </Route>
            <Route
              exact
              path={path.EMAIL_NOTIFICATION_PROFILES}
            >
              <EmailNotificationProfileList />
            </Route>
            <Route
              exact
              path={path.EMAIL_NOTIFICATION_PROFILE}
            >
              <EmailNotificationProfileDetail />
            </Route>
            <Route
              exact
              path={path.PAGERDUTY_PROFILES}
            >
              <PagerDutyProfileList />
            </Route>
            <Route
              exact
              path={path.PAGERDUTY_PROFILE}
            >
              <PagerDutyProfileDetail />
            </Route>
            <Route
              exact
              path={path.ALERT_METHODS}
            >
              <NotificationMethodList />
            </Route>
            <Route
              exact
              path={path.ALERT_METHOD}
            >
              <NotificationMethodDetail />
            </Route>
            {
              hasDeveloperAccess && (
                <Route
                  exact
                  path={path.API_KEYS}
                >
                  <ApiKeyList />
                </Route>
              )
            }
            {
              hasDeveloperAccess && (
                <Route
                  exact
                  path={path.API_KEY}
                >
                  <ApiKeyEditor />
                </Route>
              )
            }
            <Route
              exact
              path={path.PROFILE}
            >
              <Profile />
            </Route>
            <Route path="*">
              <Container>
                <h1>Page Not Found</h1>
                <p>
                  This page was not found or you do not have permission to access the page.
                </p>
              </Container>
            </Route>
          </Switch>
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
