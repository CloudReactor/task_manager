import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

import React, { lazy, useContext, Suspense } from 'react';
import {
  Route,
  Switch,
  withRouter,
  RouteComponentProps
} from 'react-router-dom';

import {
  Container
} from 'react-bootstrap/'

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import * as path from '../../constants/routes';
import { isAuth } from '../../hocs/index';

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

const RunEnvironmentList = lazy( () =>
  import('./RunEnvironment')
);

const RunEnvironmentDetail = lazy( () =>
  import('./RunEnvironmentDetail')
);

const GroupList = lazy( () =>
  import('./Group')
);

const GroupEditor = lazy( () =>
  import('./Group/GroupEditor')
);

const ApiKeyList = lazy( () =>
  import('./ApiKey')
);

const ApiKeyEditor = lazy( () =>
  import('./ApiKey/ApiKeyEditor')
);

const Profile = lazy( () =>
  import('./Profile/ProfileEditor')
);

const EmailNotificationProfileList = lazy( () =>
  import('./EmailNotificationProfile')
);

const EmailNotificationProfileDetail = lazy( () =>
  import('./EmailNotificationProfileDetail')
);

const PagerDutyProfileList = lazy( () =>
  import('./PagerDutyProfile')
);

const PagerDutyProfileDetail = lazy( () =>
  import('./PagerDutyProfileDetail')
);

const AlertMethodList = lazy( () =>
  import('./AlertMethod')
);

const AlertMethodDetail = lazy( () =>
  import('./AlertMethodDetail')
);

type PathParamsType = {
};

type Props = RouteComponentProps<PathParamsType>;

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
              render={props => <TaskList {...props} />}
            />
            <Route
              exact
              path={path.WORKFLOWS}
              render={props => <WorkflowList {...props} />}
            />
            <Route
              exact
              path={path.WORKFLOW}
              render={props => <WorkflowDetail {...props} />}
            />

            <Route
              exact
              path={path.WORKFLOW_EXECUTION}
              render={props => <WorkflowExecutionDetail {...props} />}
            />

            <Route
              exact
              path={path.TASK}
              render={props => <TaskDetail {...props} />}
            />
            <Route
              exact
              path={path.TASK_EXECUTION}
              render={props => <TaskExecutionDetail {...props} />}
            />
            <Route
              exact
              path={path.RUN_ENVIRONMENTS}
              render={props => <RunEnvironmentList {... props} />}
            />
            <Route
              exact
              path={path.RUN_ENVIRONMENT}
              render={props => <RunEnvironmentDetail {... props} />}
            />

            <Route
              exact
              path={path.GROUPS}
              render={props => <GroupList {... props} />}
            />
            <Route
              exact
              path={path.GROUP}
              render={props => <GroupEditor {... props} />}
            />
            <Route
              exact
              path={path.EMAIL_NOTIFICATION_PROFILES}
              render={props => <EmailNotificationProfileList {... props} />}
            />
            <Route
              exact
              path={path.EMAIL_NOTIFICATION_PROFILE}
              render={props => <EmailNotificationProfileDetail {... props} />}
            />
            <Route
              exact
              path={path.PAGERDUTY_PROFILES}
              render={props => <PagerDutyProfileList {... props} />}
            />
            <Route
              exact
              path={path.PAGERDUTY_PROFILE}
              render={props => <PagerDutyProfileDetail {... props} />}
            />
            <Route
              exact
              path={path.ALERT_METHODS}
              render={props => <AlertMethodList {... props} />}
            />
            <Route
              exact
              path={path.ALERT_METHOD}
              render={props => <AlertMethodDetail {... props} />}
            />
            {
              hasDeveloperAccess && (
                <Route
                  exact
                  path={path.API_KEYS}
                  render={props => <ApiKeyList {... props} />}
                />
              )
            }
            {
              hasDeveloperAccess && (
                <Route
                  exact
                  path={path.API_KEY}
                  render={props => <ApiKeyEditor {... props} />}
                />
              )
            }
            <Route
              exact
              path={path.PROFILE}
              render={props => <Profile {... props} />}
            />

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
          (process.env.REACT_APP_DEPLOYMENT !== 'production') &&
          <p>Version {process.env.REACT_APP_VERSION_SIGNATURE}</p>
        }
      </div>
    </div>
  );
}

export default withRouter(isAuth(Dashboard));
