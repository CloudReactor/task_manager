import { ACCESS_LEVEL_ADMIN } from '../../../utils/constants';
import { saveGroup, fetchGroup } from '../../../utils/api';

import * as Yup from 'yup';

import { Group } from '../../../types/website_types';
import { catchableToString } from '../../../utils';

import React, { useContext, useEffect, useState } from 'react';
import { Link, useHistory, useParams } from 'react-router-dom';
import { Formik, Form, Field, ErrorMessage } from 'formik';

import {
  Alert,
  Container,
  Col,
  Row,
} from 'react-bootstrap';

import { Button } from '@material-ui/core/';

import {
  GlobalContext
} from '../../../context/GlobalContext';

import BreadcrumbBar from '../../../components/BreadcrumbBar/BreadcrumbBar';
import Loading from '../../../components/Loading';
import FormikErrorsSummary from '../../../components/common/FormikErrorsSummary';
import GroupMembersEditor from '../../../components/GroupDetails/GroupMembersEditor';

import '../../../components/Tasks/style.scss';
import abortableHoc, { AbortSignalProps } from '../../../hocs/abortableHoc';
import AccessDenied from '../../../components/AccessDenied';

type PathParamsType = {
  id: string;
};

type Props = AbortSignalProps;

const validationSchema = Yup.object().shape({
  name: Yup.string().max(200)
    .required(),
  description: Yup.string().max(5000),
  to_addresses: Yup.array(),
  cc_addresses: Yup.array(),
  bcc_addresses: Yup.array(),
  subject_template: Yup.string().max(1000),
  body_template: Yup.string().max(1000)
});

const GroupEditor = ({
  abortSignal
}: Props) => {
  const {
    id
  } = useParams<PathParamsType>();

  const {
    currentUser,
    setCurrentUser,
    currentGroup,
    setCurrentGroup
  } = useContext(GlobalContext);

  if (!currentUser || !currentGroup) {
    return <AccessDenied />;
  }

  const [group, setGroup] = useState<Group>(currentGroup);
  const [isLoading, setLoading] = useState(false);
  const [isSaving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const history = useHistory();

  const loadGroup = async () => {
    setLoading(true);
    try {
      const fetchedGroup = await fetchGroup(parseInt(id), abortSignal);
      setGroup(fetchedGroup);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage("Failed to load Group: "  + catchableToString(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id !== 'new') {
      // user is editing existing Group profile
      loadGroup();
    }
  }, []);

  const renderGroupForm = () => {
    const creatingNew =  (id === 'new');

    const pushToGroupsIndex = () => history.push('/groups');

    return (
      <Container>
        {
          errorMessage &&
          <Alert variant="danger">
            { errorMessage }
          </Alert>
        }
        <Formik
          initialValues={group || {}}
          validationSchema={validationSchema}
          onSubmit={async (values, actions) => {
            try {
              setSaving(true);
              setErrorMessage(null);

              const createdGroup = await saveGroup(values)

              if (creatingNew) {
                currentUser.groups.push(createdGroup);
                currentUser.group_access_levels[createdGroup.id] = ACCESS_LEVEL_ADMIN;
                setCurrentUser(currentUser);
                setCurrentGroup(createdGroup);
              }

              pushToGroupsIndex();
              setErrorMessage(null);
            } catch (err) {
              console.log(err);
              setErrorMessage("Failed to save Group: "  + catchableToString(err));
            } finally {
              setSaving(false);
            }
          }}
        >
          {({
            handleSubmit,
            handleChange,
            values,
            errors,
            isValid,
            status,
            touched,
            isSubmitting,
            setFieldValue
          }) => (

            <Form noValidate onSubmit={handleSubmit}>
              <Row>
                <Col>
                  <FormikErrorsSummary errors={errors} touched={touched}
                   values={values} />
                </Col>
              </Row>
              <Row className="pb-3">
                <Col sm={3} md={2} lg={1} className="align-self-center">
                  Name
                </Col>
                <Col sm={9} md={10} lg={6} xl={5}>
                  <Field
                    type="text"
                    name="name"
                    placeholder="Give this Group a name"
                    className="form-control"
                    value={values.name}
                    onChange={handleChange}
                    required={true}
                  />
                  <ErrorMessage name="name" />
                </Col>
              </Row>

              <Row className="pb-3">
                <Col sm={3} md={2} lg={1} className="align-self-center"/>
                <Col>
                  <Button variant="outlined" color="primary" size="large" type="submit"
                   disabled={isSubmitting}>Save</Button>
                </Col>
              </Row>
            </Form>
          )}
        </Formik>
      </Container>
    );
  };

  const handleGroupMembersChanged = async () => {
    await loadGroup();
  };

  const creatingNew = (id === 'new');

  const accessLevel = group?.id ?
    (currentUser.group_access_levels[group.id] ?? null) : null;

  const isGroupAdmin = accessLevel && (accessLevel >= ACCESS_LEVEL_ADMIN);

  const breadcrumbLink = creatingNew ? 'Create New' : (group?.name || id);

  const groupsLink = <Link to="/groups">Groups</Link>

  return (
    <div>
      <BreadcrumbBar
        firstLevel={groupsLink}
        secondLevel={breadcrumbLink}
      />
      {
        (!group || isGroupAdmin || creatingNew) && (
          isLoading ? (<Loading />) :
          renderGroupForm()
        )
      }
      {
        group?.id &&
        <GroupMembersEditor group={group}
          onGroupMembersChanged={handleGroupMembersChanged} />
      }
    </div>
  );
}

export default abortableHoc(GroupEditor);
