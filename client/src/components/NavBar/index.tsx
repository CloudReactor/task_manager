import * as JwtUtils from '../../utils/jwt_utils'

import React, { Fragment, useContext } from 'react';
import { Link } from 'react-router-dom';
import Svg from 'react-inlinesvg';
import styles from './NavBar.module.scss';

import {
  Dropdown,
  Nav,
  Navbar,
  NavbarBrand,
} from 'react-bootstrap'

import * as path from '../../constants/routes';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';
import { ACCESS_LEVEL_DEVELOPER } from '../../utils/constants';

interface Props {
}

const NavBar = (p: Props) => {
  const context = useContext(GlobalContext);

  const {
    currentUser,
    currentGroup,
    setCurrentGroup
  } = context;

  if (!currentUser || !currentGroup) {
    return null;
  }

  const accessLevel = accessLevelForCurrentGroup(context);

  if (!accessLevel) {
    return null;
  }

  const switchGroup = (groupId: number) => {
    const group = currentUser.groups.find(g => g.id === groupId);
    if (group) {
      setCurrentGroup(group);
      window.location.reload();
    } else {
      console.error(`Can't find group with ID ${groupId}`);
    }
  };

  const handleLogOut = (): void => {
    JwtUtils.removeTokenContainer();
    window.location.href = '/login';
  };

  const accountLinks: {path: string, text: string}[] = [];

  if (accessLevel >= ACCESS_LEVEL_DEVELOPER) {
    accountLinks.push({
      path: path.API_KEYS,
      text: 'API Keys',
    });
  }

  accountLinks.push({
    //divider: false,
    path: path.PROFILE,
    text: 'Change password',
  });

  const notificationLinks = [
    {
      path: path.EMAIL_NOTIFICATION_PROFILES,
      text: 'Email Notification Profiles',
    }, {
      path: path.PAGERDUTY_PROFILES,
      text: 'PagerDuty Profiles',
    }, {
      path: path.ALERT_METHODS,
      text: 'Alert Methods',
    }
  ];

  return (
    <Navbar bg="dark"  variant="dark" expand="sm">
      <NavbarBrand as={Link} to={path.DASHBOARD}>
        <div className={styles.logo}>
          <Svg
            src="/images/cloudreactor_logo_light.svg"
            description="CloudReactor Logo"
          />
        </div>
      </NavbarBrand>
      <Navbar.Toggle aria-controls="basic-navbar-nav" />
      <Navbar.Collapse id="basic-navbar-nav">
        <Nav className={styles.navLinks}>
          <Link to={path.WORKFLOWS} className="nav-link">
              Workflows
          </Link>

          <Link to={path.RUN_ENVIRONMENTS} className="nav-link">
              Run Environments
          </Link>
        </Nav>
      </Navbar.Collapse>

      <Dropdown drop="left">
        <Dropdown.Toggle as="span" variant="success" id="dropdown-group" className="pointer">
          {currentGroup.name}
        </Dropdown.Toggle>

        <Dropdown.Menu>
          {
            currentUser.groups.map(group => (
              <Dropdown.Item key={group.id} onClick={() => switchGroup(group.id) }>
                {
                  (group.id === currentGroup.id) ?
                  (<span>{ group.name } <i className="fas fa-check" /></span>) :
                  (<span>{ group.name }</span>)
                }
              </Dropdown.Item>
            ))
          }

          <Dropdown.Divider />
          <Dropdown.Item as={Link} to={path.GROUPS}>
             View all Groups
          </Dropdown.Item>
        </Dropdown.Menu>

      </Dropdown>

      <Dropdown drop="left">
        <Dropdown.Toggle as="span" variant="success" id="dropdown-user" className="pointer">
          {currentUser.username}
        </Dropdown.Toggle>

        <Dropdown.Menu>
          <Dropdown.Header>
            Account
          </Dropdown.Header>

          {accountLinks.map((item, i) => {
            const {
              path,
              text
            } = item;

            return (
              <Fragment key={`nav-dropdown-${i}`}>
                <Dropdown.Item as={Link} to={path}>
                  {text}
                </Dropdown.Item>
              </Fragment>
            );
          })}

          <Dropdown.Divider />

          <Dropdown.Header>
            Notification Settings
          </Dropdown.Header>

          {notificationLinks.map((item, i) => {
            const {
              path,
              text
            } = item;

            return (
              <Fragment key={`nav-dropdown-${i}`}>
                <Dropdown.Item as={Link} to={path}>
                  {text}
                </Dropdown.Item>
              </Fragment>
            );
          })}

          <Dropdown.Divider />
          <Dropdown.Item onClick={handleLogOut}>
            Sign out
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    </Navbar>
  );
};

export default NavBar;
