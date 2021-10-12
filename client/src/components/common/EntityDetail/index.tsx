import { CancelToken } from 'axios';

import { EntityReference } from '../../../types/domain_types';
import { ACCESS_LEVEL_DEVELOPER } from '../../../utils/constants';

import {
  makeErrorElement
} from '../../../utils/api';

import React, { Component } from 'react';
import { RouteComponentProps } from 'react-router';
import { Link } from 'react-router-dom';

import {
  Alert,
  ButtonToolbar,
  Row,
  Col
} from 'react-bootstrap/'

import { createModal } from 'react-modal-promise';

import { GlobalContext, accessLevelForCurrentGroup } from '../../../context/GlobalContext';

import { CancelTokenProps } from '../../../hocs/cancelTokenHoc';
import { BootstrapVariant } from '../../../types/ui_types';
import ActionButton from '../ActionButton';
import BreadcrumbBar from '../../BreadcrumbBar/BreadcrumbBar';
import AsyncConfirmationModal from '../AsyncConfirmationModal';
import Loading from '../../Loading';

type PathParamsType = {
  uuid: string;
};

export type EntityDetailProps = RouteComponentProps<PathParamsType> & CancelTokenProps & {
};

export interface EntityDetailState<T extends EntityReference> {
  entity?: T,
  flashBody?: any;
  flashAlertVariant?: BootstrapVariant;
  isLoading: boolean;
  isCloning: boolean;
  isDeleting: boolean;
  isSaving: boolean;
}

export abstract class EntityDetail<T extends EntityReference>
    extends Component<EntityDetailProps, EntityDetailState<T>> {
  static contextType = GlobalContext;

  constructor(props: EntityDetailProps, entityName: string) {
    super(props);

    this.entityName = entityName;

    const path = props.location.pathname;
    this.listPath = path.substring(0, path.lastIndexOf('/'));

    this.state = {
      isLoading: false,
      isCloning: false,
      isDeleting: false,
      isSaving: false
    };
  }

  readonly entityName: string;
  readonly listPath: string;
  abstract fetchEntity(uuid: string, cancelToken: CancelToken): Promise<T>
  abstract cloneEntity(uuid: string, values: any, cancelToken: CancelToken): Promise<T>
  abstract deleteEntity(uuid: string, cancelToken: CancelToken): Promise<void>

  componentDidMount() {
    document.title = `CloudReactor - ${this.entityName} Details`

    const uuid = this.props.match.params.uuid;

    if (uuid === 'new') {
      document.title = `CloudReactor - Create ${this.entityName}`
    } else {
      this.loadEntity(uuid);
    }
  }

  async loadEntity(uuid: string) {
    const {
      cancelToken
    } = this.props;

    this.setState({
      isLoading: true
    });
    try {
      const entity = await this.fetchEntity(uuid, cancelToken);
      this.setState({
        entity,
        isLoading: false
      });
    } catch (ex) {
      this.setState({
        flashBody: `Failed to load ${this.entityName}: ` + ex.message,
        flashAlertVariant: 'danger',
        isLoading: false
      });
    }
  }

  public render() {
    const accessLevel = accessLevelForCurrentGroup(this.context);

    if (!accessLevel) {
      return null;
    }

    const {
      entity,
      isLoading,
      isCloning,
      isDeleting,
      isSaving,
      flashBody,
      flashAlertVariant
    } = this.state;

    const breadcrumbLink = this.props.match.params.uuid === 'new' ?
      'Create New' : entity?.name;

    const EntitysLink = <Link to={this.listPath}>{ this.entityName }</Link>

    return (
      <div>
        <BreadcrumbBar
         firstLevel={EntitysLink}
         secondLevel={breadcrumbLink} />

        {
          (accessLevel >= ACCESS_LEVEL_DEVELOPER) &&
          <Row>
            <Col>
              <ButtonToolbar>
                <ActionButton
                  faIconName="clone" label="Clone" action="clone"
                  disabled={isCloning || isDeleting || !entity} inProgress={isCloning}
                  onActionRequested={this.handleActionRequested} />

                <ActionButton cbData={entity} action="delete"
                  disabled={isCloning || isDeleting || !entity}
                  onActionRequested={this.handleActionRequested}
                  faIconName="trash" label="Delete"
                  inProgress={isDeleting} />
              </ButtonToolbar>
            </Col>
          </Row>
        }

        {
          flashBody && !isLoading && !isDeleting && !isCloning && !isSaving &&
          <Alert
            variant={flashAlertVariant || 'success'}
            onClose={() => {
              this.setState({
                flashBody: undefined
              });
            }}
            dismissible>
            {flashBody}
          </Alert>
        }

        {
          (entity || (this.props.match.params.uuid === 'new')) ? this.renderEntity() :
          (<Loading />)
        }
      </div>

    );
  }

  // Should be overridden
  abstract renderEntity(): any

  handleActionRequested = async (action: string | undefined, cbData: any):
    Promise<void> => {
    switch (action) {
        case 'clone':
        this.setState({
          flashBody: undefined
        });
        return await this.handleCloneRequested();

        case 'delete':
        this.setState({
          flashBody: undefined
        });
        return await this.handleDeletionRequested();

      default:
        console.error(`Unknown action '${action}'`);
        break;
    }
  }

  handleCloneRequested = async () => {
    const {
      entity
    } = this.state;

    if (!entity) {
      console.error(`No ${this.entityName} to clone`);
      return;
    }

    const modal = createModal(AsyncConfirmationModal);

    // TODO: extra warning if removing current user

    const rv = await modal({
      title: `Clone ${this.entityName}`,
      confirmLabel: 'Clone',
      faIconName: 'copy',
      children: (
        <p>
          Clone the {this.entityName} '{entity.name}'?
        </p>
      )
    });

    if (rv) {
      return await this.handleCloneConfirmed();
    }
  }

  handleCloneConfirmed = async () => {
    const {
      entity
    } = this.state;

    if (!entity) {
      console.error(`No ${this.entityName} to clone`);
      return;
    }

    this.setState({
      isCloning: true,
      flashBody: undefined
    });

    try {
      const cloned = await this.cloneEntity(entity.uuid, {
      }, this.props.cancelToken);

      this.setState({
        entity: cloned,
        isCloning: false,
        flashBody: `${this.entityName} '${entity.name}' has been cloned.`,
        flashAlertVariant: 'info'
      });

      this.props.history.push(this.listPath + '/' +
        encodeURIComponent(cloned.uuid));
    } catch (ex) {
      const flashBody = makeErrorElement(ex);

      this.setState({
        isCloning: false,
        flashAlertVariant: 'danger',
        flashBody
      });
    }
  }

  handleDeletionRequested = async () => {
    const {
      entity
    } = this.state;

    if (!entity) {
      console.error(`No ${this.entityName} to delete`);
      return;
    }

    const modal = createModal(AsyncConfirmationModal);

    const rv = await modal({
      title: `Delete ${this.entityName}`,
      confirmLabel: 'Delete',
      faIconName: 'trash',
      children: (
        <p>
          Are you sure you want to delete the {this.entityName} '{entity.name}'?
          All Tasks and Workflows using this {this.entityName} won't use
          this {this.entityName} anymore.
        </p>
      )
    });

    if (rv) {
      return await this.handleDeletionConfirmed();
    }
  }

  handleDeletionConfirmed = async () => {
    const {
      entity
    } = this.state;

    if (!entity) {
      console.error(`No ${this.entityName} to delete`);
      return;
    }

    this.setState({
      isDeleting: true,
      flashBody: undefined
    });

    try {
      await this.deleteEntity(entity.uuid, this.props.cancelToken);

      this.setState({
        isDeleting: false,
        flashBody: `${this.entityName} '${entity.name}' has been deleted.`,
        flashAlertVariant: 'info'
      }, this.pushToListView);
    } catch (ex) {
      const flashBody = makeErrorElement(ex);

      this.setState({
        isDeleting: false,
        flashAlertVariant: 'danger',
        flashBody
      });
    }
  }

  handleSaveStarted = () => {
    this.setState({
      isSaving: true,
      flashBody: undefined
    });
  };

  handleSaveSuccess = (entity: T) => {
    this.setState({
      isSaving: false,
      flashBody: undefined
    }, this.pushToListView);
  };

  handleSaveError = (ex: Error, values: any) => {
    const flashBody = makeErrorElement(ex);

    this.setState({
      isSaving: false,
      flashAlertVariant: 'danger',
      flashBody
    });
  };

  pushToListView = () => {
    this.props.history.push(this.listPath);
  };
}
