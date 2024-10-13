import * as C from '../../../utils/constants';

import React, { Component } from "react";
import { Formik, Form, Field, ErrorMessage } from 'formik';
import * as Yup from 'yup';

import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';
import _ from 'lodash';

interface Props {
  edge: any | null;
  workflowTransition: any | null
  size?: string;
  isOpen: boolean;
  onSave: (wt: any) => void;
  onCancel: () => void;
  onRemove: (edge: any | null, wt: any | null) => void;}

interface State {
  open: boolean;
  workflowTransition: any
}

const DEFAULT_RULE_TYPE = 'success';

const RULE_TYPE_ALWAYS = 'always';
const RULE_TYPE_ON_SUCCESS = 'success';
const RULE_TYPE_ON_FAILURE = 'failure';
const RULE_TYPE_ON_TIMEOUT = 'timeout';
const RULE_TYPE_ON_EXIT_CODE = 'exit_code';
const RULE_TYPE_THRESHOLD = 'threshold';
const RULE_TYPE_CUSTOM = 'custom';
const RULE_TYPE_DEFAULT = 'default';

const ALL_RULE_TYPES = [
  RULE_TYPE_ALWAYS,
  RULE_TYPE_ON_SUCCESS,
  RULE_TYPE_ON_FAILURE,
  RULE_TYPE_ON_TIMEOUT,
  RULE_TYPE_ON_EXIT_CODE,
  RULE_TYPE_THRESHOLD,
  RULE_TYPE_CUSTOM,
  RULE_TYPE_DEFAULT
];

const workflowTransitionSchema = Yup.object().shape({
  ruleType: Yup.string()
    .required('Rule type is required')
});

export default class WorkflowTransitionEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  context: any;

  constructor(props: Props) {
    super(props);

    this.state = {
      open: props.isOpen,
      workflowTransition: props.workflowTransition ?? {}
    };
  }

  static getDerivedStateFromProps(props, state) {
    return {
      open: props.isOpen,
      workflowTransition: props.workflowTransition ?? {}
    };
  }

  handleOpen = () => {
    this.setState({ open: true });
  }

  handleClose = () => {
    this.setState({ open: false });
  }

  toggle = () => {
    this.props.onCancel();
  }

  handleRemoveAndClose = () => {
    this.props.onRemove(this.props.edge, this.props.workflowTransition);
  };

  public render() {
    const accessLevel = accessLevelForCurrentGroup(this.context);
    const canSave = accessLevel && (accessLevel >= C.ACCESS_LEVEL_DEVELOPER);

    const {
      edge
    } = this.props;

    console.dir(edge);

    const {
      open,
      workflowTransition
    } = this.state;

    const ruleType = (workflowTransition ? workflowTransition.rule_type : '') || DEFAULT_RULE_TYPE;

    return (
      <Modal show={open} onHide={this.toggle}>

        <Modal.Header closeButton>
          <Modal.Title>
            Workflow Transition Configuration
          </Modal.Title>
        </Modal.Header>

        <Formik
         initialValues={ {ruleType} }
         enableReinitialize={true}
         validationSchema={workflowTransitionSchema}
         onSubmit={(values, actions) => {
           console.log('onSubmit, values = ');
           console.dir(values);
           //console.log('onSubmit, values = ');
           //console.dir(actions);

           const wt = workflowTransition || {};
           wt.rule_type = values.ruleType;

           this.handleSave(wt);
         }}
         render={({
          errors, status, touched, submitForm, isSubmitting
        }) => (
          <Form>
            <Modal.Body>
              <fieldset disabled={!canSave}>
                <div className="form-group">
                  <label>Rule Type</label>
                  <Field name="ruleType"
                  component="select" className="form-control">
                    <option value="" key="">Select a Rule Type</option>
                    {
                      ALL_RULE_TYPES.map(ruleType => {
                        return (
                          <option value={ruleType} key={ruleType}>
                            {ruleType}
                          </option>
                        );
                      })
                    }
                  </Field>
                  <ErrorMessage name="ruleType" component="span" className="help-block" />
                </div>
              </fieldset>
            </Modal.Body>

            <Modal.Footer>
              <Button variant="secondary" onClick={this.toggle}>
                { canSave ? 'Cancel' : 'Close' }
              </Button>

              {
                canSave && this.props.workflowTransition && (
                  <Button variant="danger"
                   onClick={this.handleRemoveAndClose}>
                   <i className="fa fa-trash" /> Remove
                  </Button>
                )
              }

              {
                canSave && (
                  <Button variant="primary" onClick={submitForm}>
                    <i className={"fa fa-" + (this.props.workflowTransition ? 'bolt' : 'plus')} />
                    &nbsp;
                    {
                      this.props.workflowTransition ?
                      (isSubmitting ? 'Updating ...' : 'Update') :
                      (isSubmitting ? 'Adding ...' : 'Add')
                    }
                  </Button>
                )
              }
            </Modal.Footer>
          </Form>
        )} />
      </Modal>
    );
  }

  handleRuleTypeChange = (event: any) => {
    console.log('handleRuleTypeChange');
  }

  handleSave = (wt: any) => {
    console.log('handleSave');
    console.dir(wt);
    this.setState({
      workflowTransition: this.props.workflowTransition || {},
    }, () => {
      this.props.onSave(wt);
    });
  }
}
