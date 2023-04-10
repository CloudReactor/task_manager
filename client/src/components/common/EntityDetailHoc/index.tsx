import pluralize from "pluralize";

import { EntityReference } from '../../../types/domain_types';
import { ACCESS_LEVEL_DEVELOPER } from '../../../utils/constants';

import {
  makeErrorElement
} from '../../../utils/api';

import React, {  useContext, useEffect, useState } from 'react';
import { Link, useHistory, useLocation, useParams } from 'react-router-dom';

import {
  Alert,
  ButtonToolbar,
  Row,
  Col
} from 'react-bootstrap/'

import { createModal } from 'react-modal-promise';

import { GlobalContext, accessLevelForCurrentGroup } from '../../../context/GlobalContext';

import { AbortSignalProps } from '../../../hocs/abortableHoc';
import { BootstrapVariant } from '../../../types/ui_types';
import ActionButton from '../ActionButton';
import BreadcrumbBar from '../../BreadcrumbBar/BreadcrumbBar';
import AsyncConfirmationModal from '../AsyncConfirmationModal';
import Loading from '../../Loading';

type PathParamsType = {
  uuid: string;
};

export interface EntityDetailConfig<T extends EntityReference> {
  entityName: string;
  fetchEntity: (uuid: string, abortSignal: AbortSignal) => Promise<T>;
  cloneEntity: (uuid: string, values: any, abortSignal: AbortSignal) => Promise<T>;
  deleteEntity: (uuid: string, abortSignal: AbortSignal) => Promise<void>;
}

export type EntityDetailProps<T extends EntityReference> = AbortSignalProps & {
  entity: T | null;
  onSaveStarted: (T) => void;
  onSaveSuccess: (T) => void;
  onSaveError: (ex: unknown, values: any) => void;
}


export const makeEntityDetailComponent = <T extends EntityReference>(
  WrappedComponent: React.ComponentType<EntityDetailProps<T>>, config: EntityDetailConfig<T>) => {

  const EntityDetail = (props: AbortSignalProps) => {
    const context = useContext(GlobalContext);

    const accessLevel = accessLevelForCurrentGroup(context);

    if (!accessLevel) {
      return null;
    }

    const {
      abortSignal
    } = props;

    const {
      entityName,
      fetchEntity,
      cloneEntity,
      deleteEntity
    } = config;

    const [entity, setEntity] = useState<T | null>(null);
    const [flashBody, setFlashBody] = useState<string | null>(null);
    const [flashAlertVariant, setFlashAlertVariant] = useState<BootstrapVariant>('info');
    const [isLoading, setLoading] = useState(false);
    const [isCloning, setCloning] = useState(false);
    const [isDeleting, setDeleting] = useState(false);
    const [isSaving, setSaving] = useState(false);

    const location = useLocation();
    const path = location.pathname;
    const listPath = path.substring(0, path.lastIndexOf('/'));

    const {
      uuid
    }  = useParams<PathParamsType>();

    const history = useHistory();

    const loadEntity = async () => {
      setLoading(true);

      try {
        const fetchedEntity = await fetchEntity(uuid, abortSignal);
        setEntity(fetchedEntity);
        setLoading(false);
      } catch (ex) {
        const message = (ex instanceof Error) ? ex.message :
          ((typeof ex === 'string') ? ex : 'Unknown error');

        setFlashBody(`Failed to load ${entityName}: ` + message);
        setFlashAlertVariant('danger'),
        setLoading(false);
      }
    }


    const handleCloneRequested = async () => {
      if (!entity) {
        console.error(`No ${entityName} to clone`);
        return;
      }

      const modal = createModal(AsyncConfirmationModal);

      // TODO: extra warning if removing current user

      const rv = await modal({
        title: `Clone ${entityName}`,
        confirmLabel: 'Clone',
        faIconName: 'copy',
        children: (
          <p>
            Clone the {entityName} &lsquo;{entity.name}&rsquo;?
          </p>
        )
      });

      if (rv) {
        return await handleCloneConfirmed();
      }
    }

    const handleCloneConfirmed = async () => {
      if (!entity) {
        console.error(`No ${entityName} to clone`);
        return;
      }

      setCloning(true);
      setFlashBody(null);

      try {
        const cloned = await cloneEntity(entity.uuid, {
        }, abortSignal);

        setEntity(cloned);
        setCloning(false);
        setFlashBody(`${entityName} '${entity.name}' has been cloned.`);
        setFlashAlertVariant('info');

        history.push(listPath + '/' + encodeURIComponent(cloned.uuid));
      } catch (ex) {
        setCloning(false);
        setFlashAlertVariant('danger')
        setFlashBody(makeErrorElement(ex));
      }
    }

    const pushToListView = () => {
      history.push(listPath);
    };

    const handleDeletionConfirmed = async () => {
      if (!entity) {
        console.error(`No ${entityName} to delete`);
        return;
      }

      setDeleting(true);
      setFlashBody(null);

      try {
        await deleteEntity(entity.uuid, abortSignal);

        setDeleting(false);
        setFlashBody(`${entityName} '${entity.name}' has been deleted.`);
        setFlashAlertVariant('info');
        pushToListView();
      } catch (ex) {
        setDeleting(false);
        setFlashBody(makeErrorElement(ex));
        setFlashAlertVariant('danger');
      }
    }

    const handleDeletionRequested = async () => {
      if (!entity) {
        console.error(`No ${entityName} to delete`);
        return;
      }

      const modal = createModal(AsyncConfirmationModal);

      const rv = await modal({
        title: `Delete ${entityName}`,
        confirmLabel: 'Delete',
        faIconName: 'trash',
        children: (
          <p>
            Are you sure you want to delete the {entityName} &lsquo;{entity.name}&rsquo;?
            All Tasks and Workflows using this {entityName} won&apos;t use
            this {entityName} anymore.
          </p>
        )
      });

      if (rv) {
        return await handleDeletionConfirmed();
      }
    }

    const handleSaveStarted = (t: T) => {
      setSaving(true);
      setFlashBody(null);
    };

    const handleSaveSuccess = (t: T) => {
      setSaving(false);
      setFlashBody(null);
      pushToListView();
    };

    const handleSaveError = (ex: unknown, values: any) => {
      setSaving(false);
      setFlashBody(makeErrorElement(ex));
      setFlashAlertVariant('danger');
    };

    const handleActionRequested = async (action: string | undefined, cbData: any):
      Promise<void> => {
      switch (action) {
          case 'clone':
          setFlashBody(null);
          return await handleCloneRequested();

          case 'delete':
          setFlashBody(null);
          return await handleDeletionRequested();

        default:
          console.error(`Unknown action '${action}'`);
          break;
      }
    }


    useEffect(() => {
      if (uuid === 'new') {
        document.title = `CloudReactor - Create ${entityName}`
      } else if (!entity && !isLoading) {
        loadEntity();
      }
    });

    const breadcrumbLink = (uuid === 'new') ?
      'Create New' : entity?.name;

    const EntitysLink = <Link to={listPath}>{ pluralize(entityName) }</Link>

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
                  onActionRequested={handleActionRequested} />

                <ActionButton cbData={entity} action="delete"
                  disabled={isCloning || isDeleting || !entity}
                  onActionRequested={handleActionRequested}
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
              setFlashBody(null);
            }}
            dismissible>
            {flashBody}
          </Alert>
        }

        {
          (entity || (uuid === 'new')) ? (
            <WrappedComponent entity={entity}
             onSaveStarted={handleSaveStarted}
             onSaveSuccess={handleSaveSuccess}
             onSaveError={handleSaveError}
             {...props} />
          ) :
          (<Loading />)
        }
      </div>
    );
  }
  return EntityDetail;
}
