import * as C from '../../utils/constants';
import { Group, User } from  '../../types/website_types';
import {
  ResultsPage,
  fetchUsers,
  saveInvitation,
  removeUserFromGroup,
  updateGroupAccessLevelOfUser
} from '../../utils/api';

import { ACCESS_LEVEL_ADMIN } from '../../utils/constants';

import React, { Component, Fragment } from 'react';

import {
  Alert,
  Button, ButtonGroup, ButtonToolbar,
  Row, Col
} from 'react-bootstrap';

import BootstrapTable from 'react-bootstrap-table-next-react18-node20';
import cellEditFactory, { Type } from 'react-bootstrap-table2-editor-react18-node20';

import { create } from 'react-modal-promise';

import {
  GlobalContext
} from '../../context/GlobalContext';

import { BootstrapVariant } from '../../types/ui_types';

import * as UIC from '../../utils/ui_constants';

import AsyncConfirmationModal from '../../components/common/AsyncConfirmationModal';

import GroupInvitationForm from './GroupInvitationForm';

interface Props {
  group: Group,
  onGroupMembersChanged: () => Promise<void>
}

interface State {
  q?: string;
  sortBy?: string;
  descending: boolean;
  userPage?: ResultsPage<User>;
  currentPage: number;
  rowsPerPage: number;
  selectedUsernames: string[];
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
}

class GroupMembersEditor extends Component<Props, State> {
  context: any;
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    this.state = {
      descending: false,
      currentPage: 0,
      rowsPerPage: UIC.DEFAULT_PAGE_SIZE,
      selectedUsernames: []
    };
  }

  componentDidMount() {
    this.loadUsers();
  }

  public render() {
    const {
      group,
    } = this.props;

    const {
      q,
      sortBy,
      descending,
      userPage,
      flashBody,
      flashAlertVariant
    } = this.state;

    if (!userPage) {
      return <p>Loading ...</p>;
    }

    const {
      currentUser
    } = this.context;

    const accessLevel = group?.id ?
      (currentUser?.group_access_levels[group.id] ?? null) : null;

    const isGroupAdmin = accessLevel && (accessLevel >= ACCESS_LEVEL_ADMIN);

    const accessLevelOptions = Object.entries(C.ACCESS_LEVEL_TO_ROLE_NAME).map(
      ([accessLevel, roleName]) => (
        {
          label: roleName,
          value: '' + accessLevel
        }
      ));

    const columns: any[] = [
      {
        dataField: 'username',
        text: 'User'
      }, {
        dataField: 'accessLevel',
        text: 'Access Level',
        formatter: (accessLevel: string, row: any, rowIndex: number,
          extraData: any) => C.ACCESS_LEVEL_TO_ROLE_NAME[accessLevel],
        editor: {
          type: Type.SELECT,
          options: accessLevelOptions
        }
      }
    ];

    if (isGroupAdmin) {
      columns.push({
        dataField: 'actions',
        text: 'Actions',
        formatter: (username: string, row: any, rowIndex: number, extraData: any) => (
          <ButtonToolbar>
            <ButtonGroup size="sm" className="mr-2">
              <Button onClick={() => {
                  this.handleRemovalRequested(username);
                }}>
                <i className="fa fa-user-minus" /> Remove
              </Button>
            </ButtonGroup>
          </ButtonToolbar>
        )
      });
    }

    return (
      <Fragment>
        {
          flashBody &&
          <Alert variant={flashAlertVariant || 'success'}>
            {flashBody}
          </Alert>
        }

        <h3>Members</h3>

        <Row>
          <Col sm="6" lg="4" xl="3">
            <input type="search"
              className="form-control p-2 search"
              onChange={this.handleQueryChanged}
              onKeyDown={keyEvent => {
                if (keyEvent.key === 'Enter') {
                  this.loadUsers();
                }
              }}
              placeholder="Search"
              value={q}
            />
          </Col>
        </Row>

        <Row>
          <Col>
            <BootstrapTable keyField='username' data={ this.mapUsersPageToTableData(userPage) }
             columns={columns} striped={true} bootstrap4={true}
             cellEdit={ isGroupAdmin ? cellEditFactory({
               mode: 'click',
               blurToSave: true,
               afterSaveCell: this.handleAccessLevelChangeRequested
             }) : undefined } />
          </Col>
        </Row>

        {
          isGroupAdmin && (
            <Fragment>
              <h4>Invite a new member</h4>
              <Row>
                <Col>
                  <GroupInvitationForm group={group}
                  onSubmit={this.handleInvitationSubmitted} />
                </Col>
              </Row>
            </Fragment>
          )
        }
      </Fragment>
    );
  }

  loadUsers = async () => {
    const {
      group
    } = this.props;

    const {
      q,
      sortBy,
      descending,
      currentPage,
      rowsPerPage
    } = this.state;

    try {
      const userPage = await fetchUsers({
        groupId: group.id,
        q,
        sortBy,
        descending,
        offset: currentPage * UIC.DEFAULT_PAGE_SIZE,
        maxResults: rowsPerPage
      });
      this.setState({
        userPage
      });

    } catch (error) {
      console.log(error);
    }
  }

  mapUsersPageToTableData = (usersPage: ResultsPage<User>) => {
    return usersPage.results.map(user => {
      const username = user.username;
      return {
        username,
        accessLevel: '' + this.accessLevelForUsername(username),
        actions: username
      };
    });
  }

  accessLevelForUsername = (username: string) => {
    const {
      group
    } = this.props;

    if (group && group.user_access_levels) {
      const ual = group.user_access_levels.find(x => {
        return (x.user.username === username);
      });

      return ual ? ual.access_level : C.ACCESS_LEVEL_OBSERVER;
    } else {
      return C.ACCESS_LEVEL_OBSERVER;
    }
  }

  handleQueryChanged = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({
      q: event.currentTarget.value
    });
  }


  handleAccessLevelChangeRequested = async (oldAccessLevelString: any, newAccessLevelString: any, row: any, column: any) => {
    if (column.dataField !== 'accessLevel') {
      return;
    }

    if (oldAccessLevelString === newAccessLevelString) {
      return;
    }

    const {
      group,
      onGroupMembersChanged
    } = this.props;

    const username = row.username;

    // TODO: check if the username is the same as the current user, if so,
    // ask for confirmation.

    this.setState({
      flashBody: undefined
    });

    try {
      const accessLevel = parseInt(newAccessLevelString);

      await updateGroupAccessLevelOfUser(username, group.name, accessLevel);

      this.setState({
        flashBody: `${row.username} was granted access level '${C.ACCESS_LEVEL_TO_ROLE_NAME[newAccessLevelString]}' in Group '${group.name}'.`,
        flashAlertVariant: 'success'
      });

      await onGroupMembersChanged();
    } catch (ex) {
       this.setState({
        flashBody: `An error occurred updating the access level for ${username}.`,
        flashAlertVariant: 'warning'
      });
    }
  }

  handleRemovalRequested = async (username: string) => {
    const {
      group
    } = this.props;

    const modal = create(AsyncConfirmationModal);

    // TODO: extra warning if removing current user

    const rv = await modal({
      title: 'Remove User from Group',
      confirmLabel: 'Remove',
      faIconName: 'user-minus',
      children: (
        <p>
          Are you sure you want to remove the User &lsquo;{username}&rsquo; from the Group
          &lsquo;{group.name}&rsquo;? This user will lose all access to Tasks and Workflows
          in the Group.
        </p>
      )
    });

    if (rv) {
      return await this.handleRemovalConfirmed(username);
    }
  }

  handleRemovalConfirmed = async (username: string) => {
    const {
      group,
      onGroupMembersChanged
    } = this.props;

    this.setState({
      flashBody: undefined
    });

    try {
      await removeUserFromGroup(username, group.name);

      this.setState({
        flashBody: `${username} has been removed from the Group '${group.name}'.`,
        flashAlertVariant: 'info'
      });

      await onGroupMembersChanged();
      await this.loadUsers();
    } catch (ex) {
      this.setState({
        flashBody: `An error occurred removing the User ${username} from the Group '${group.name}'.`,
        flashAlertVariant: 'warning'
      });
    }
  }

  handleInvitationSubmitted = async (values: any) => {
    this.setState({
      flashBody: undefined
    });

    try {
      const invitedNewUser = await saveInvitation(values) ;

      const roleName =
        C.ACCESS_LEVEL_TO_ROLE_NAME[
        '' + (values.group_access_level || C.ACCESS_LEVEL_OBSERVER)];

      const flashBody = invitedNewUser ?
        `Sent invitation to ${values.to_email}.` :
        `${values.to_email} was granted ${roleName} access.`;

      this.setState({
        flashBody,
        flashAlertVariant: 'success'
      });

      if (!invitedNewUser) {
        await this.props.onGroupMembersChanged();
        await this.loadUsers();
      }
    } catch (error) {
      this.setState({
        flashBody: 'An error occurred sending the invitation.',
        flashAlertVariant: 'warning'
      });
      throw error;
    }
  }
}

export default GroupMembersEditor;