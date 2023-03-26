import * as JwtUtils from '../utils/jwt_utils'
import { makeConfiguredClient } from '../axios_config';
import { fetchCurrentUser } from '../utils/api';

import React from 'react';
import { RouteComponentProps } from 'react-router';

import {
  GlobalContext,
  getSavedCurrentGroupId
} from '../context/GlobalContext';

type PathParamsType = Record<string, never>;

type Props = RouteComponentProps<PathParamsType>;

interface State {
}

export const isAuth = <P extends object>(
    WrappedComponent: React.ComponentType<P>) =>
  class extends React.Component<P & Props, State> {
    static contextType = GlobalContext;

    async componentDidMount() {
      const {
        history,
      } = this.props;

      const {
        currentUser,
        setCurrentUser,
        setCurrentGroup
      } = this.context;

      if (currentUser) {
        return;
      }

      let success = false;

      try {
        const tokenContainer = JwtUtils.readTokenContainer();
        const token = tokenContainer.access;

        if (token) {
          await makeConfiguredClient().post('auth/jwt/verify/', {
            token
          });

          const user = await fetchCurrentUser();

          setCurrentUser(user);

          const savedCurrentGroupId = getSavedCurrentGroupId();

          let group = user.groups[0];

          if (savedCurrentGroupId) {
            const foundGroup = user.groups.find(g => g.id === savedCurrentGroupId);
            group = foundGroup ?? group
          }

          setCurrentGroup(group);

          success = true;
        } else {
          console.log('No access token found');
        }
      } catch (error) {
        console.log('Token verification failed');
      }

      if (!success) {
        JwtUtils.removeTokenContainer();
        history.push('/login');
      }
    }

    public render() {
      const {
        history,
        location,
        match,
        staticContext,
        ...props
      } = this.props;
      return <WrappedComponent {...props as P} />;
    }
  };
