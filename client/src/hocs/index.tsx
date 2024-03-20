import * as JwtUtils from '../utils/jwt_utils'
import { makeConfiguredClient } from '../axios_config';
import { fetchCurrentUser } from '../utils/api';

import React, { useContext, useEffect } from 'react';

import { useLocation, useNavigate } from 'react-router-dom';

import {
  GlobalContext,
  getSavedCurrentGroupId
} from '../context/GlobalContext';

export default function isAuth<P extends object>(
    WrappedComponent: React.ComponentType<P>): React.ComponentType<P> {
  const AuthenticatedComponent = (props: P) => {
    const {
      currentUser,
      setCurrentUser,
      setCurrentGroup
    } = useContext(GlobalContext);

    const history = useNavigate();
    const location = useLocation();

    useEffect(() => {
      if (currentUser) {
        return;
      }

      async function verifyAuthentication() {
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
          history('/login?next=' + encodeURIComponent(
            location.pathname + location.search + location.hash));
        }
      }

      verifyAuthentication();
    }, []);

    return <WrappedComponent {...props} />;
  };

  return AuthenticatedComponent;
}
