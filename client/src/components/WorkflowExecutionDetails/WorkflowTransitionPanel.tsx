import {
  WorkflowTransition,
  WorkflowTransitionEvaluation
} from "../../types/domain_types";

import React, { Component, Fragment }  from 'react';

import {
  Row,
  Col
} from 'react-bootstrap'

import { timeFormat } from '../../utils';

interface Props {
  workflowTransition: WorkflowTransition,
  // should be sorted from most recent to least recent
  evaluations: WorkflowTransitionEvaluation[]
}

interface State {
}

export default class WorkflowTransitionPanel extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    this.state = {
    };
  }

  public render() {
    const {
      workflowTransition,
      evaluations
    } = this.props;

    const wt = workflowTransition;

    const latestEvaluation = (evaluations.length > 0) ? evaluations[0] : null;

    return (
      <Fragment>
        <Row>
          <Col>
             <h4>Transition Properties</h4>
          </Col>
        </Row>
        <Row>
          <Col>
            <dl>
              <dt>Rule Type</dt>
              <dd>{wt.rule_type}</dd>
            </dl>

            <dl>
              <dt>Latest Evaluation Result</dt>
              <dd>
                {
                  latestEvaluation ?
                  (
                    latestEvaluation.result ?
                    (<span><i className="fas fa-check" />&nbsp;Taken</span>) :
                    (<span><i className="fas fa-times" />&nbsp;NOT Taken</span>)
                  ) :
                  'Never evaluated'
                }
              </dd>

              {
                latestEvaluation && (
                  <Fragment>
                    <dt>Evaluated at</dt>
                    <dd>{ timeFormat(latestEvaluation.evaluated_at, true) }</dd>
                  </Fragment>
                )
              }
            </dl>
          </Col>
        </Row>
      </Fragment>
    );
  }
}