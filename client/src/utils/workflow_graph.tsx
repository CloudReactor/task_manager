import moment from 'moment';

import {
  Workflow,
  WorkflowExecution,
  WorkflowTaskInstance,
  WorkflowTaskInstanceExecution,
  WorkflowTransition, WorkflowTransitionEvaluation
} from '../types/domain_types';

import React from 'react';
import {IEdge, IGraphInput, INode} from "react-digraph";

export function makeGraph(workflow: Workflow, workflowExecution?: WorkflowExecution) : [
  IGraphInput,
  any,
  any,
  any,
  any
] {
  const nodes: INode[] = [];
  const nodeIdsToWorkflowTaskInstances: any = {};
  const edgeToWorkflowTransitions: any = {};
  const wtiUuidToExecutions: any = {};
  const wtUuidToEvaluations: any = {};

  if (workflowExecution) {
    workflowExecution.workflow_task_instance_executions.forEach((wptie: WorkflowTaskInstanceExecution) => {
      const wtiUuid = wptie.workflow_task_instance.uuid;
      if (!wtiUuidToExecutions[wtiUuid]) {
        wtiUuidToExecutions[wtiUuid] = [];
      }
      wtiUuidToExecutions[wtiUuid].push(wptie);
    });

    workflowExecution.workflow_transition_evaluations.forEach((wte: WorkflowTransitionEvaluation) => {
      const wtUuid = wte.workflow_transition.uuid;
      if (!wtUuidToEvaluations[wtUuid]) {
        wtUuidToEvaluations[wtUuid] = []
      }
      wtUuidToEvaluations[wtUuid].push(wte);
    });

    // Order executions from most recent to least recent
    Object.keys(wtiUuidToExecutions).forEach(wptiUuid => {
      const wties = wtiUuidToExecutions[wptiUuid];
      wties.sort((wtie1: WorkflowTaskInstanceExecution, wtie2: WorkflowTaskInstanceExecution) => {
        const t1 = moment(wtie1.created_at).valueOf();
        const t2 = moment(wtie2.created_at).valueOf();

        if (t1 > t2) {
          return -1;
        } else if (t1 === t2) {
          return 0;
        } else {
          return 1;
        }
      });
    });

    // Order evaluations from most recent to least recent
    Object.keys(wtUuidToEvaluations).forEach(wtUuid => {
      const wtes = wtUuidToEvaluations[wtUuid];
      wtes.sort((wte1: WorkflowTransitionEvaluation, wte2: WorkflowTransitionEvaluation) => {
        const t1 = moment(wte1.evaluated_at).valueOf();
        const t2 = moment(wte2.evaluated_at).valueOf();

        if (t1 > t2) {
          return -1;
        } else if (t1 === t2) {
          return 0;
        } else {
          return 1;
        }
      });
    });
  }

  let i = 0;
  (workflow.workflow_task_instances ??
   workflow.workflow_process_type_instances ?? [])
  .forEach((wti: WorkflowTaskInstance) => {
    const nodeType = workflowExecution ?
       computeNodeTypeForNode(wti, wtiUuidToExecutions) : 'empty';
    nodes.push({
       id: wti.uuid,
       title: wti.name,
       x: wti.ui_center_margin_left || (i * 350 + 100),
       y: wti.ui_center_margin_top || 100,
       type: nodeType
     });

    nodeIdsToWorkflowTaskInstances[wti.uuid] = wti;

    i += 1;
  });

  const edges: IEdge[] = [];

  workflow.workflow_transitions.forEach((wt: WorkflowTransition) => {
    const fromWtiUuid = (wt.from_workflow_task_instance ??
      wt.from_workflow_process_type_instance ?? {uuid: ''}).uuid;
    const toWtiUuid = (wt.to_workflow_task_instance ??
      wt.to_workflow_process_type_instance ?? {uuid: ''}).uuid;

    edges.push({
      source: fromWtiUuid,
      target: toWtiUuid,
      handleText: wt.rule_type,
      type: 'emptyEdge'
    });

    const edgeKey = fromWtiUuid + '%%' + toWtiUuid;

    edgeToWorkflowTransitions[edgeKey] = wt;
  });

  const graph = {
    nodes,
    edges
  };

  return [
    graph,
    nodeIdsToWorkflowTaskInstances,
    edgeToWorkflowTransitions,
    wtiUuidToExecutions,
    wtUuidToEvaluations
  ];
}



export const GraphConfig =  {
  NodeTypes: {
    empty: { // required to show empty nodes
      typeText: null,
      shapeId: "#empty", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="empty" key="0">
          <ellipse cx="100" cy="100" rx="90" ry="45"></ellipse>
        </symbol>
      )
    },
    running: {
      typeText: null,
      shapeId: "#running", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="running" key="1">
          <ellipse cx="100" cy="100" rx="90" ry="45"
           fill="rgba(96, 255, 96, 0.12)">
            <animate
             attributeType="XML"
             attributeName="fill"
             values="#282;#6d6;#282;#282"
             dur="0.8s"
             repeatCount="indefinite"/>
          </ellipse>
        </symbol>
      )
    },
    succeeded: {
      typeText: null,
      shapeId: "#succeeded", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="succeeded" key="1">
          <ellipse cx="100" cy="100" rx="90" ry="45"
           fill="rgba(96, 255, 96, 0.12)">
          </ellipse>
        </symbol>
      )
    },
    failed: {
      typeText: null,
      shapeId: "#failed", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="failed" key="2">
          <ellipse cx="100" cy="100" rx="90" ry="45"
           fill="rgba(255, 96, 96, 0.12)"></ellipse>
        </symbol>
      )
    },
    terminatedAfterTimeOut: {
      typeText: null,
      shapeId: "#terminatedAfterTimeOut", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="terminatedAfterTimeOut" key="3">
          <ellipse cx="100" cy="100" rx="90" ry="45"
           fill="rgba(180, 180, 96, 0.12)">
          </ellipse>
        </symbol>
      )
    },
    notExecuted: {
      typeText: null,
      shapeId: "#notExecuted", // relates to the type property of a node
      shape: (
        <symbol viewBox="0 0 200 200" id="notExecuted" key="3">
          <ellipse cx="100" cy="100" rx="90" ry="45" strokeDasharray="5"></ellipse>
        </symbol>
      )
    }
  },
  NodeSubtypes: {},
  EdgeTypes: {
    emptyEdge: {  // required to show empty edges
      shapeId: "#emptyEdge",
      shape: (
        <symbol viewBox="0 0 50 50" id="emptyEdge" key="0">
        </symbol>
      )
    }
  }
}

export const NODE_KEY = 'id';       // Allows D3 to correctly update DOM

export function computeEdgeKey(edge: IEdge) : string {
  const {
    source,
    target
  } = edge;

  if (!source && !target) {
    return '';
  }

  return source + '%%' + target;
}

export function computeNodeTypeForNode(wpti: WorkflowTaskInstance,
  wptiUuidToExecutions: any): string {
  const wpties = wptiUuidToExecutions[wpti.uuid];

  if (!wpties) {
    return 'notExecuted';
  }

  const wptie = wpties[0];

  if (!wptie || !wptie.task_execution) {
    return 'notExecuted';
  }

  const status = wptie.task_execution.status.replace(/_+/g, '-').toLowerCase();

  switch (status) {
    case 'manually-started':
      return 'running';

    case 'running':
    case 'succeeded':
    case 'failed':
      return status;

    case 'terminated-after-time-out':
      return 'terminatedAfterTimeOut';

    default:
      return 'failed';
  }
}

export const EDGE_CLASS_NOT_EVALUATED = 'not-evaluated';
export const EDGE_CLASS_TAKEN = 'taken';
export const EDGE_CLASS_NOT_TAKEN = 'not-taken';

export const ALL_EDGE_CLASSES = [
   EDGE_CLASS_NOT_EVALUATED,
   EDGE_CLASS_TAKEN,
   EDGE_CLASS_NOT_TAKEN
]

export function computeEdgeClassForEdge(wt: WorkflowTransition,
  wtUuidToEvaluations: any): string {
  const wts = wtUuidToEvaluations[wt.uuid];

  if (!wts) {
    return EDGE_CLASS_NOT_EVALUATED;
  }

  const wte = wts[0];

  if (!wte) {
    return EDGE_CLASS_NOT_EVALUATED;
  }

  if (wte.result) {
     return EDGE_CLASS_TAKEN;
  }

  return EDGE_CLASS_NOT_TAKEN;
}

// Helper to find the index of a given node
export const getNodeIndex = (searchNode: INode | any, graph: IGraphInput) => {
  return graph.nodes.findIndex(node => {
    return node[NODE_KEY] === searchNode[NODE_KEY];
  });
}

// Helper to find the index of a given edge
export const getEdgeIndex = (searchEdge: IEdge, graph: IGraphInput) => {
  return graph.edges.findIndex(edge => {
    return (
      edge.source === searchEdge.source && edge.target === searchEdge.target
    );
  });
}

// Given a nodeKey, return the corresponding node
export const getViewNode = (nodeKey: string, graph: IGraphInput) => {
  const searchNode: any = {};

  searchNode[NODE_KEY] = nodeKey;
  const i = getNodeIndex(searchNode, graph);

  return graph.nodes[i];
}
