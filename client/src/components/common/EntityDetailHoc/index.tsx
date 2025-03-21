import pluralize from "pluralize";

import { EntityReference } from '../../../types/domain_types';
import { catchableToString } from '../../../utils';
import { ACCESS_LEVEL_DEVELOPER } from '../../../utils/constants';

import {
  makeErrorElement
} from '../../../utils/api';

import React, { useCallback, useContext, useEffect, useState } from 'react';
import { Link, useNavigate, useLocation, useParams } from 'react-router-dom';

import {
  Alert,
  ButtonToolbar,
  Row,
  Col
} from 'react-bootstrap/'

import { create } from 'react-modal-promise';

import { GlobalContext, accessLevelForCurrentGroup } from '../../../context/GlobalContext';

import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';
import { BootstrapVariant } from '../../../types/ui_types';
import ActionButton from '../ActionButton';
import BreadcrumbBar from '../../BreadcrumbBar/BreadcrumbBar';
import AsyncConfirmationModal from '../AsyncConfirmationModal';
import AccessDenied from '../../AccessDenied';
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

export interface EntityDetailInnerProps<T extends EntityReference> extends AbortSignalProps {
  entity: T | null;
  onSaveStarted: (T) => void;
  onSaveSuccess: (T) => void;
  onSaveError: (err: unknown, values: any) => void;
}

export const makeEntityDetailComponent = <T extends EntityReference, P>(
  WrappedComponent: React.ComponentType<React.PropsWithChildren<P & EntityDetailInnerProps<T>>>, config: EntityDetailConfig<T>) => {

  const EntityDetail = (props: P & AbortSignalProps) => {
    const context = useContext(GlobalContext);

    const accessLevel = accessLevelForCurrentGroup(context);

    if (!accessLevel) {
      return <AccessDenied />;
    }

    const {
      abortSignal,
      ...rest
    } = props;

    const pRest = rest as unknown as P;

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
    const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
    const [isCloning, setCloning] = useState(false);
    const [isDeleting, setDeleting] = useState(false);
    const [isSaving, setSaving] = useState(false);

    const location = useLocation();
    const path = location.pathname;
    const listPath = path.substring(0, path.lastIndexOf('/'));

    const {
      uuid
    }  = useParams<PathParamsType>();

    if (!uuid) {
      return <div>Invalid UUID</div>;
    }

    const navigate = useNavigate();

    const loadEntity = useCallback(async () => {
      setLoading(true);
      setLoadErrorMessage(null);

      try {
        const fetchedEntity = await fetchEntity(uuid, abortSignal);
        setEntity(fetchedEntity);
        setFlashBody(null);
      } catch (ex) {
        const message = `Failed to load ${entityName}: ` + catchableToString(ex);
        setLoadErrorMessage(message);
        setFlashBody(message);
        setFlashAlertVariant('danger');
      } finally {
        setLoading(false);
      }
    }, [uuid, abortSignal])


    const handleCloneRequested = useCallback(async () => {
      if (!entity) {
        console.error(`No ${entityName} to clone`);
        return;
      }

      const modal = create(AsyncConfirmationModal);

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
    }, [entity]);

    const handleCloneConfirmed = useCallback(async () => {
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

        navigate(listPath + '/' + encodeURIComponent(cloned.uuid));
      } catch (ex) {
        setCloning(false);
        setFlashAlertVariant('danger')
        setFlashBody(makeErrorElement(ex));
      }
    }, [entity, abortSignal, navigate])

    const pushToListView = useCallback(() => {
      navigate(listPath);
    }, [navigate, listPath]);

    const handleDeletionConfirmed = useCallback(async () => {
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
    }, [entity, abortSignal])

    const handleDeletionRequested = useCallback(async () => {
      if (!entity) {
        console.error(`No ${entityName} to delete`);
        return;
      }

      const modal = create(AsyncConfirmationModal);

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
    }, [entity]);

    const handleSaveStarted = useCallback((t: T) => {
      setSaving(true);
      setFlashBody(null);
    }, []);

    const handleSaveSuccess = useCallback((t: T) => {
      setSaving(false);
      setFlashBody(null);
      pushToListView();
    }, []);

    const handleSaveError = useCallback((ex: unknown, values: any) => {
      setSaving(false);
      setFlashBody(makeErrorElement(ex));
      setFlashAlertVariant('danger');
    }, []);

    const handleActionRequested = useCallback(async (action: string | undefined, cbData: any):
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
    }, [handleCloneRequested, handleDeletionRequested]);


    useEffect(() => {
      if (uuid === 'new') {
        document.title = `CloudReactor - Create ${entityName}`
      } else if (!entity && !isLoading && !loadErrorMessage) {
        document.title = `CloudReactor - Loading ${entityName} ...`
        loadEntity();
      } else {
        document.title = `CloudReactor - ${entityName} not found`
      }
    }, [entity, isLoading, loadErrorMessage]);

    const breadcrumbLink = (uuid === 'new') ?
      'Create New' : entity?.name;

    const EntitiesLink = <Link to={listPath}>{ pluralize(entityName) }</Link>

    return (
      <div>
        <BreadcrumbBar
         firstLevel={EntitiesLink}
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
            <WrappedComponent abortSignal={abortSignal} entity={entity}
             onSaveStarted={handleSaveStarted}
             onSaveSuccess={handleSaveSuccess}
             onSaveError={handleSaveError}
             {...pRest} />
          ) :
          (<Loading />)
        }
      </div>
    );
  }
  return abortableHoc(EntityDetail);
}
