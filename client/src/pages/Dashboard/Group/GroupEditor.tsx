import { ACCESS_LEVEL_ADMIN } from '../../../utils/constants';
import { saveGroup, fetchGroup } from '../../../utils/api';

import * as Yup from 'yup';

import { Group } from '../../../types/website_types';

import React, { Component } from 'react';
import { withRouter, RouteComponentProps } from 'react-router';
import { Link } from 'react-router-dom'
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
import FormikErrorsSummary from '../../../components/common/FormikErrorsSummary';
import GroupMembersEditor from '../../../components/GroupDetails/GroupMembersEditor';

import '../../../components/Tasks/style.scss';

type PathParamsType = {
  id: string;
};

type Props = RouteComponentProps<PathParamsType> & {
}

interface State {
  group: Group | any;
  isLoading: boolean;
  errorMessage?: string;
  isSaving: boolean;
}

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

class GroupEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
      super(props);

      this.state = {
        group: null,
        isLoading: false,
        isSaving: false
      };
  }

  componentDidMount() {
    const id = this.props.match.params.id;

    if (id === 'new') {
      // user is creating new Group
      // create group object matching form fields; Formik requires, even though inputs are empty
      this.setState({
        group: {}
      })
    } else {
      // user is editing existing Group profile
      this.loadGroup(parseInt(id));
    }
  }

  async loadGroup(id: number) {
    this.setState({
      isLoading: true
    });
    try {
      const group = await fetchGroup(id);

      this.setState({
        group,
        errorMessage: undefined,
        isLoading: false
      });
    } catch (ex) {
      this.setState({
        errorMessage: "Failed to load Group: " + ex.message,
        isLoading: false
      });
    }
  }

  renderGroupForm() {
    const {
      group,
      errorMessage
    } = this.state;

    const creatingNew =  (this.props.match.params.id === 'new');

    const pushToGroupsIndex = () =>
      this.props.history.push('/groups');

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
              this.setState({
                isSaving: true,
                errorMessage: undefined
              });

              const createdGroup = await saveGroup(values)

              if (creatingNew) {
                const {
                  currentUser,
                  setCurrentUser,
                  setCurrentGroup
                } = this.context;

                currentUser.groups.push(createdGroup);
                currentUser.group_access_levels[createdGroup.id] = ACCESS_LEVEL_ADMIN;
                setCurrentUser(currentUser);
                setCurrentGroup(createdGroup);
              }

              pushToGroupsIndex();

              this.setState({
                errorMessage: undefined,
                isSaving: false
              });
            } catch (error) {
              console.log(error);
              this.setState({
                errorMessage: "Failed to save Group: " + error.message,
                isSaving: false
              });
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
  }

  public render() {
    const {
      group
    } = this.state;

     const {
      currentUser
    } = this.context;

    const creatingNew = (this.props.match.params.id === 'new');

    const accessLevel = group?.id ?
      (currentUser.group_access_levels[group.id] ?? null) : null;

    const isGroupAdmin = accessLevel && (accessLevel >= ACCESS_LEVEL_ADMIN);

    const breadcrumbLink = creatingNew ? 'Create New' :
       (group?.name || this.props.match.params.id);

    const groupsLink = <Link to="/groups">Groups</Link>

    return (
      <div>
        <BreadcrumbBar
         firstLevel={groupsLink}
         secondLevel={breadcrumbLink}
        />
        {
          (!group || isGroupAdmin || creatingNew) && (
            this.state.isLoading ? (<div>Loading ...</div>) :
            this.renderGroupForm()
          )
        }
        {
          group?.id &&
          <GroupMembersEditor group={group}
           onGroupMembersChanged={this.handleGroupMembersChanged} />
        }
      </div>
    );
  }

  handleGroupMembersChanged = async () => {
    const id = this.props.match.params.id;
    await this.loadGroup(parseInt(id));
  }
}

export default withRouter(GroupEditor);