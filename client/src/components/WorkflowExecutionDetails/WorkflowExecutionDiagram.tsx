import {
  WorkflowTaskInstance,
  WorkflowTransition,
  WorkflowExecution
} from "../../types/domain_types";

import React, { Component }  from 'react';

import {
  Row,
  Col
} from 'react-bootstrap'

import {
  GraphView,
  IGraphInput,
  IEdge,
  GraphUtils,
  SelectionT
} from 'react-digraph';

import WorkflowTaskInstancePanel from './WorkflowTaskInstancePanel';
import WorkflowTransitionPanel from './WorkflowTransitionPanel';
import { startWorkflowTaskInstances } from '../../utils/api';
import * as WorkflowGraph from '../../utils/workflow_graph';

interface Props {
  workflowExecution: WorkflowExecution;
  onWorkflowExecutionUpdated: (uuid: string, workflowExecution?: WorkflowExecution) => void;
}

interface State {
  graph: IGraphInput;
  copiedNode: any;
  selected: any;
  lastSelectionAt: number | null;
  selectedWorkflowTaskInstance: WorkflowTaskInstance | null;
  isTaskInstancePanelOpen: boolean;
  selectedWorkflowTransition: WorkflowTransition | null;
  isTransitionPanelOpen: boolean;
  viewEdgeToEdit: IEdge | null;
  nodeIdsToWorkflowTaskInstances: any;
  edgeToWorkflowTransitions: any;
  wptiUuidToExecutions: any;
  wtUuidToEvaluations: any;
}

export default class WorkflowExecutionDiagram extends Component<Props, State> {
  constructor(props: Props) {
    super(props);

    const [
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions,
      wptiUuidToExecutions,
      wtUuidToEvaluations
    ] = WorkflowGraph.makeGraph(props.workflowExecution.workflow_snapshot,
                                props.workflowExecution);

    this.state = {
      graph,
      selected: {},
      lastSelectionAt: null,
      copiedNode: null,
      selectedWorkflowTaskInstance: null,
      isTaskInstancePanelOpen: false,
      selectedWorkflowTransition: null,
      isTransitionPanelOpen: false,
      viewEdgeToEdit: null,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions,
      wptiUuidToExecutions,
      wtUuidToEvaluations
    };
  }

  componentDidUpdate(prevProps: Readonly<Props>, prevState: Readonly<State>, snapshot?: any) {
    if (this.props.workflowExecution !== prevProps.workflowExecution) {
      const [
        graph,
        nodeIdsToWorkflowTaskInstances,
        edgeToWorkflowTransitions,
        wptiUuidToExecutions,
        wtUuidToEvaluations
      ] = WorkflowGraph.makeGraph(
            this.props.workflowExecution.workflow_snapshot,
            this.props.workflowExecution);

      this.setState({
        graph,
        nodeIdsToWorkflowTaskInstances,
        edgeToWorkflowTransitions,
        wptiUuidToExecutions,
        wtUuidToEvaluations
      });
    }
  }

  public render() {
    const {
      wptiUuidToExecutions,
      wtUuidToEvaluations,
      graph,
      selected,
      selectedWorkflowTaskInstance,
      isTaskInstancePanelOpen,
      selectedWorkflowTransition,
      isTransitionPanelOpen
    } = this.state;

    const nodes = graph.nodes;
    const edges = graph.edges;

    const NodeTypes = WorkflowGraph.GraphConfig.NodeTypes;
    const NodeSubtypes = WorkflowGraph.GraphConfig.NodeSubtypes;
    const EdgeTypes = WorkflowGraph.GraphConfig.EdgeTypes;

    return (
      <Row>
        <Col md={8} lg={9}>
          <div id='graph' className="graph-view">
            <GraphView  nodeKey={WorkflowGraph.NODE_KEY}
                        nodes={nodes}
                        edges={edges}
                        selected={selected}
                        nodeTypes={NodeTypes}
                        nodeSubtypes={NodeSubtypes}
                        edgeTypes={EdgeTypes}
                        minZoom={0.5}
                        maxZoom={1.25}
                        nodeSize={200}
                        renderNodeText={this.renderNodeText}
                        afterRenderEdge={this.afterRenderEdge}
                        readOnly={true}
                        onSelect={this.onSelect}
                        zoomDelay={0}
                        zoomDur={500} />
          </div>
        </Col>
        <Col md={4} lg={3}>
        {

          (isTaskInstancePanelOpen && selectedWorkflowTaskInstance) ?
            <WorkflowTaskInstancePanel workflowTaskInstance={selectedWorkflowTaskInstance}
             executions={wptiUuidToExecutions[selectedWorkflowTaskInstance.uuid] || []}
             onStartRequested={this.handleStartWorkflowTaskInstanceRequested} />
          : (isTransitionPanelOpen && selectedWorkflowTransition) ? (
            <WorkflowTransitionPanel workflowTransition={selectedWorkflowTransition}
             evaluations={wtUuidToEvaluations[selectedWorkflowTransition.uuid] || []} />
          )  : (
            <div className="d-flex flex-column justify-content-center h-100">
              <div className="p-2">
                Select a Task Instance (node) or Transition (edge) to view
                its properties or perform actions on it.
              </div>
            </div>
          )
        }
        </Col>
      </Row>
    );
  }

  renderNodeText = (data: any, id: string | number, isSelected: boolean) => {
    const title = data.title;
    const className = GraphUtils.classNames('node-text', {
      selected: isSelected,
    });

    const {
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    const wti = nodeIdsToWorkflowTaskInstances[data.id];
    const taskName = (wti && wti.task) ? wti.task.name : '';

    return (
      <text className={className} textAnchor="middle">
        {title && (

            <tspan x={0} dy={-5} fontSize="13px">
              {title.length > 30
                  ? title.substr(0, 30)
                  : title}
            </tspan>
        )}
        { taskName && (
            <tspan x={0} dy={15} fontSize="11px">
              {taskName}
            </tspan>
          )
        }
        {title && <title>{title}</title>}
        {wti && wti.task && <title>{wti.task.name}</title>}
      </text>
    );
  }

  afterRenderEdge = (
    id: string,
    element: any,
    edge: IEdge,
    edgeContainer: any,
    isEdgeSelected: boolean
  ): void => {
    const {
      edgeToWorkflowTransitions,
      wtUuidToEvaluations
    } = this.state;

    const edgeKey = WorkflowGraph.computeEdgeKey(edge);

    const wt = edgeToWorkflowTransitions[edgeKey];

    if (wt) {
      const edgeClass = WorkflowGraph.computeEdgeClassForEdge(wt, wtUuidToEvaluations);
      edgeContainer.classList.remove(...WorkflowGraph.ALL_EDGE_CLASSES);
      edgeContainer.classList.add(edgeClass);
    } else {
      console.log(`No wt found for edge key ${edgeKey}`);
    }
  }

  onSelect = (selected: SelectionT, event?: any) => {
    console.log('onSelect');

    const {
      nodes,
      edges
    } = selected;

    let isMultiSelect = false;

    if (nodes && (nodes.size > 1)) {
      isMultiSelect = true;
      this.setState({
        selected: null,
        selectedWorkflowTaskInstance: null
      });
    }

    if (edges && (edges.size > 1)) {
      isMultiSelect = true;
      this.setState({
        selectedWorkflowTransition: null,
        isTransitionPanelOpen: false
      });
    }

    if (isMultiSelect) {
      return;
    }

    if (!nodes || (nodes.size === 0)) {
      this.setState({
        selected: null,
        selectedWorkflowTaskInstance: null
      });
    }

    if (!edges || (edges.size === 0)) {
      this.setState({
        selectedWorkflowTransition: null,
        isTransitionPanelOpen: false
      });
    }

    if (nodes && (nodes.size === 1)) {
      const {
        nodeIdsToWorkflowTaskInstances
      } = this.state;

      let {
        selectedWorkflowTaskInstance,
        isTaskInstancePanelOpen,
      } = this.state;

      const viewNodeId = nodes.keys().next().value;
      const viewNode = nodes.values().next().value;

      if (viewNode) {
        selectedWorkflowTaskInstance = nodeIdsToWorkflowTaskInstances[viewNodeId];
        isTaskInstancePanelOpen = !!selectedWorkflowTaskInstance;
      }

      // Deselect events will send Null viewNode
      this.setState({
        selected: viewNode,
        selectedWorkflowTaskInstance,
        selectedWorkflowTransition: null,
        isTaskInstancePanelOpen,
        isTransitionPanelOpen: false
      });
    }

    if (edges && (edges.size === 1)) {
      const {
        edgeToWorkflowTransitions
      } = this.state;

      let {
        selectedWorkflowTransition,
        isTransitionPanelOpen,
        viewEdgeToEdit
      } = this.state;

      const viewEdge = edges.values().next().value;

      const viewEdgeKey = viewEdge ? WorkflowGraph.computeEdgeKey(viewEdge) : '';

      if (viewEdge) {
        selectedWorkflowTransition = edgeToWorkflowTransitions[viewEdgeKey];
        isTransitionPanelOpen = !!selectedWorkflowTransition;
        viewEdgeToEdit = viewEdge;
      }

      this.setState({
        selected: viewEdge,
        selectedWorkflowTaskInstance: null,
        selectedWorkflowTransition,
        isTaskInstancePanelOpen: false,
        isTransitionPanelOpen,
        viewEdgeToEdit
      });
    }
  }

  handleStartWorkflowTaskInstanceRequested = async (wpti: WorkflowTaskInstance) => {
    const {
      workflowExecution,
      onWorkflowExecutionUpdated
    } = this.props;

    const updatedWorkflowExecution = await startWorkflowTaskInstances(workflowExecution.uuid,
      [wpti.uuid]);

    onWorkflowExecutionUpdated(workflowExecution.uuid, updatedWorkflowExecution);
  }

}
