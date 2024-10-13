import _ from 'lodash';

import * as C from '../../../utils/constants';

import {
  Workflow,
  WorkflowTaskInstance,
  WorkflowTransition,
  WorkflowExecution
} from "../../../types/domain_types";

import React, { Component, Fragment }  from 'react';
import ReactDOM, { createPortal } from 'react-dom';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../../context/GlobalContext';

import WorkflowTaskInstanceEditor from './WorkflowTaskInstanceEditor';
import WorkflowTransitionEditor from './WorkflowTransitionEditor';

import {
  GraphView,
  IGraphInput,
  IEdge,
  INode,
  GraphUtils,
  SelectionT
} from 'react-digraph';

import * as WorkflowGraph from '../../../utils/workflow_graph';

interface Props {
  workflow: Workflow;
  workflowExecution?: WorkflowExecution,
  runEnvironmentUuid: string | null,
  onGraphChanged: (
    workflowTaskInstances: WorkflowTaskInstance[],
    workflowTransitions: WorkflowTransition[]) => void;
}

interface State {
  graph: IGraphInput;
  copiedNode: any;
  selectedNode: any;
  lastSelectionAt: number | null;
  workflowTaskInstanceToEdit: any;
  isTaskInstanceEditorOpen: boolean;
  workflowTransitionToEdit: any;
  isTransitionEditorOpen: boolean;
  selectedEdge: IEdge | null;
  savedX: number | null;
  savedY: number | null;
  nodeIdsToWorkflowTaskInstances: any;
  edgeToWorkflowTransitions: any;
  modalDiv: any;
}

const DOUBLE_CLICK_DELAY_MILLIS = 500;

export default class WorkflowGraphEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  context: any;

  constructor(props: Props) {
    super(props);

    const [
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions
    ] = WorkflowGraph.makeGraph(props.workflow, props.workflowExecution);

    this.state = {
      graph,
      selectedNode: null,
      lastSelectionAt: null,
      copiedNode: null,
      workflowTaskInstanceToEdit: null,
      isTaskInstanceEditorOpen: false,
      workflowTransitionToEdit: null,
      isTransitionEditorOpen: false,
      selectedEdge: null,
      savedX: null,
      savedY: null,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions,
      modalDiv: document.createElement('div')
    };
  }

  componentDidUpdate(prevProps: Readonly<Props>, prevState: Readonly<State>, snapshot?: any) {
    if ((this.props.workflow !== prevProps.workflow) ||
        (this.props.workflowExecution !== prevProps.workflowExecution)) {
      console.log('WorkflowGraphEditor.componentDidUpdate: updating graph');

      const [
        graph,
        nodeIdsToWorkflowTaskInstances,
        edgeToWorkflowTransitions
      ] = WorkflowGraph.makeGraph(this.props.workflow,
            this.props.workflowExecution);

      this.setState({
        graph,
        nodeIdsToWorkflowTaskInstances,
        edgeToWorkflowTransitions
      });
    } else {
      console.log('WorkflowGraphEditor.componentDidUpdate: NOT updating graph');
    }
  }

  componentDidMount() {
    // Append the element into the DOM on mount. We'll render
    // into the modal container element (see the HTML tab).
    this.getModalRoot().appendChild(this.state.modalDiv);
  }

  componentWillUnmount() {
    // Remove the element from the DOM when we unmount
    this.getModalRoot().removeChild(this.state.modalDiv);
  }

  public render() {
    const {
      runEnvironmentUuid
    } = this.props;

    const accessLevel = accessLevelForCurrentGroup(this.context);
    const readOnly = !accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER);

    const {
      graph,
      selectedNode,
      workflowTaskInstanceToEdit,
      isTaskInstanceEditorOpen,
      selectedEdge,
      workflowTransitionToEdit,
      isTransitionEditorOpen,
      modalDiv
    } = this.state;

    console.log('WorkflowGraphEditor rendering');

    const {
      nodes,
      edges
    } = graph;

    /*
    const selected = graph.selected;

    console.log('Selected = ');
    console.dir(selected); */

    const NodeTypes = WorkflowGraph.GraphConfig.NodeTypes;
    const NodeSubtypes = WorkflowGraph.GraphConfig.NodeSubtypes;
    const EdgeTypes = WorkflowGraph.GraphConfig.EdgeTypes;

    return (
      <div>
        <div id='graph' className="graph-view">
          <GraphView  nodeKey={WorkflowGraph.NODE_KEY}
                      nodes={nodes}
                      edges={edges}
                      nodeTypes={NodeTypes}
                      nodeSubtypes={NodeSubtypes}
                      edgeTypes={EdgeTypes}
                      minZoom={0.5}
                      maxZoom={1.25}
                      nodeSize={200}
                      renderNodeText={this.renderNodeText}
                      readOnly={readOnly}
                      onSelect={this.onSelect}
                      onCreateNode={this.onCreateNode}
                      onUpdateNode={this.onUpdateNode}
                      canDeleteSelected={this.canDeleteSelected}
                      onDeleteSelected={this.onDeleteSelected}
                      onCreateEdge={this.onCreateEdge}
                      onSwapEdge={this.onSwapEdge}
                      onUndo={this.onUndo}
                      zoomDelay={0}
                      zoomDur={500} />
        </div>

        {
          createPortal(
            <Fragment>
              <WorkflowTaskInstanceEditor
               node={selectedNode}
               workflowTaskInstance={workflowTaskInstanceToEdit}
               runEnvironmentUuid={runEnvironmentUuid}
               isOpen={isTaskInstanceEditorOpen}
               onSave={this.onTaskInstanceModalSaved}
               onCancel={this.onTaskInstanceModalCancelled}
               onDelete={this.onTaskInstanceDeleted} />

              <WorkflowTransitionEditor
               edge={selectedEdge}
               workflowTransition={workflowTransitionToEdit}
               isOpen={isTransitionEditorOpen}
               onSave={this.onTransitionModalSaved}
               onCancel={this.onTransitionModalCancelled}
               onRemove={this.onTransitionDeleted} />
            </Fragment>,
            modalDiv
          )
        }
      </div>
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

            <tspan x={0} dy={0} fontSize="12px">
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
        {wti?.task && <title>{wti.task.name}</title>}
      </text>
  );
  }

  onSelect = (selected: SelectionT, event?: any) => {
    console.log('onSelect');

    console.dir(selected)

    const {
      nodes,
      edges
    } = selected;

    const {
      selectedNode: selection,
      lastSelectionAt,
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    let isMultiSelect = false;

    if (nodes && (nodes.size > 1)) {
      isMultiSelect = true;
      this.setState({
        selectedNode: null,
        workflowTaskInstanceToEdit: null,
        isTaskInstanceEditorOpen: false
      });
    }

    if (edges && (edges.size > 1)) {
      isMultiSelect = true;
      this.setState({
        workflowTransitionToEdit: null,
        selectedEdge: null,
        isTransitionEditorOpen: false
      });
    }

    if (isMultiSelect) {
      return;
    }

    if (!nodes || (nodes.size === 0)) {
      this.setState({
        selectedNode: null,
        workflowTaskInstanceToEdit: null,
        isTaskInstanceEditorOpen: false
      });
    }

    if (!edges || (edges.size === 0)) {
      this.setState({
        workflowTransitionToEdit: null,
        selectedEdge: null,
        isTransitionEditorOpen: false
      });
    }

    if (nodes && (nodes.size === 1)) {
      let {
        workflowTaskInstanceToEdit,
        isTaskInstanceEditorOpen,
        savedX,
        savedY
      } = this.state;

      const viewNodeId = nodes.keys().next().value;
      const viewNode = nodes.values().next().value;

      const now = new Date().getTime();

      if (viewNode && selection && (selection.id === viewNodeId) &&
          lastSelectionAt && (lastSelectionAt + DOUBLE_CLICK_DELAY_MILLIS > now )) {
        console.log('Double click of node');

        workflowTaskInstanceToEdit = nodeIdsToWorkflowTaskInstances[viewNode.id];
        isTaskInstanceEditorOpen = true;
        savedX = viewNode.x ?? 0;
        savedY = viewNode.y ?? 0;
        console.log('wti to edit = ');
        console.dir(workflowTaskInstanceToEdit);
      }

      // Deselect events will send Null viewNode
      this.setState({
        selectedNode: viewNode,
        lastSelectionAt: now,
        workflowTaskInstanceToEdit,
        isTaskInstanceEditorOpen,
        savedX,
        savedY
      });
    }

    if (edges && (edges.size === 1)) {
      const {
        lastSelectionAt,
        edgeToWorkflowTransitions
      } = this.state;

      let {
        workflowTransitionToEdit,
        isTransitionEditorOpen,
        selectedEdge
      } = this.state;

      const now = new Date().getTime();

      const viewEdge = edges.values().next().value;

      const viewEdgeKey = viewEdge ? WorkflowGraph.computeEdgeKey(viewEdge) : '';
      const selectedEdgeKey = selection ? WorkflowGraph.computeEdgeKey(selection) : '';

      console.log(`VEK = '${viewEdgeKey}', SEK = '${selectedEdgeKey}'`);

      if (viewEdge && (selectedEdgeKey === viewEdgeKey) &&
          lastSelectionAt && (lastSelectionAt + DOUBLE_CLICK_DELAY_MILLIS > now )) {
        console.log('Double click of edge');

        workflowTransitionToEdit = edgeToWorkflowTransitions[viewEdgeKey];
        isTransitionEditorOpen = true;
        selectedEdge = viewEdge;
      }

      this.setState({
        selectedNode: viewEdge,
        lastSelectionAt: now,
        workflowTransitionToEdit,
        isTransitionEditorOpen,
        selectedEdge
      });
    }
  }

  onCreateNode = (x: number, y: number) => {
    console.log('onCreateNode');

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    this.setState({
      workflowTaskInstanceToEdit: null,
      isTaskInstanceEditorOpen: true,
      savedX: x,
      savedY: y
    });
  }

  onUpdateNode = (viewNode: INode) => {
    console.log('onUpdateNode');

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    const {
      x,
      y
    } = viewNode;

    const {
      graph,
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    const pti = nodeIdsToWorkflowTaskInstances[viewNode.id];

    if (pti) {
      pti.ui_center_margin_left = x;
      pti.ui_center_margin_top = y;
    } else {
      console.warn(`Can't find Task instance for UUID ${viewNode.id}`);
    }

    const i = WorkflowGraph.getNodeIndex(viewNode, graph);

    graph.nodes[i] = viewNode;
    this.setState({
      graph,
      nodeIdsToWorkflowTaskInstances
    }, this.updateParentWithGraph);
  }

  canDeleteSelected = (selected: SelectionT) => {
    console.log('canDeleteSelected');
    return true;
  };

  removeNode = (nodeId: string) => {
    const {
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions
    } = this.state;

    delete nodeIdsToWorkflowTaskInstances[nodeId];

    // Delete any connected edges
    const newEdges = graph.edges.filter((edge, i) => {
      return (
        edge.source !== nodeId && edge.target !== nodeId
      );
    });

    graph.edges.forEach(edge => {
      if ((edge.source === nodeId) || (edge.target === nodeId)) {
        const edgeKey = WorkflowGraph.computeEdgeKey(edge);
        delete edgeToWorkflowTransitions[edgeKey];
      }
    })

    const newNodes = graph.nodes.filter((node, i) => {
      return node.id !== nodeId;
    });

    graph.nodes = newNodes;
    graph.edges = newEdges;

    this.setState({
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions,
      selectedNode: null
    }, this.updateParentWithGraph);
  }

  removeEdge = (edge: any) => {
    const {
      graph,
      edgeToWorkflowTransitions
    } = this.state;

    const edgeKey = WorkflowGraph.computeEdgeKey(edge);

    const newEdges = graph.edges.filter((existingEdge, i) => {
      return WorkflowGraph.computeEdgeKey(existingEdge) !== edgeKey;
    });

    graph.edges = newEdges;

    delete edgeToWorkflowTransitions[edgeKey];

    this.setState({
      graph,
      edgeToWorkflowTransitions,
      selectedNode: null,
      selectedEdge: null
    }, this.updateParentWithGraph);
  };

  onDeleteSelected = (selected: SelectionT) => {
    // After upgrading to react-digraph 9.x, this was added instead of
    // onDeleteNode(), but it is not triggering.

    console.log('onDeleteSelected');

    const {
      nodes,
      edges
    } = selected;

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    const {
      graph,
      edgeToWorkflowTransitions
    } = this.state;

    console.dir(nodes);

    //debugger;


    if (nodes) {
      for (const [nodeId, node] of nodes) {
        this.removeNode(nodeId);
      }
    }

    if (edges) {
      for (const [edgeId, edge] of edges) {
        this.removeEdge(edge);
      }
    }
  }

  onCreateEdge = (sourceViewNode: INode, targetViewNode: INode) => {
    console.log('onCreateEdge');

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    const source = sourceViewNode[WorkflowGraph.NODE_KEY];
    const target = targetViewNode[WorkflowGraph.NODE_KEY];

    // Only add the edge when the source node is not the same as the target
    if (source === target) {
      console.log('onCreateEdge(): Source and target nodes are the same, skipping creation');
      return;
    }

    // This is just an example - any sort of logic
    // could be used here to determine edge type
    const type = 'emptyEdge';

    const selectedEdge = {
      source,
      target,
      type,
      handleText: '[pending]'
    };

    const {
      graph
    } = this.state;

    graph.edges = [...graph.edges, selectedEdge];

    this.setState({
      isTransitionEditorOpen: true,
      selectedEdge
    });
  }

  // Called when an edge is reattached to a different target.
  onSwapEdge = (
    sourceViewNode: INode,
    targetViewNode: INode,
    viewEdge: IEdge
  ) => {
    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }


    // TODO
    console.warn('onSwapEdge not supported yet');

    /*
    console.log('onSwapEdge');

    const graph = this.state.graph;
    const i = this.getEdgeIndex(viewEdge);
    const edge = JSON.parse(JSON.stringify(graph.edges[i]));

    edge.source = sourceViewNode[NODE_KEY];
    edge.target = targetViewNode[NODE_KEY];
    graph.edges[i] = edge;
    // reassign the array reference if you want the graph to re-render a swapped edge
    graph.edges = [...graph.edges];

    this.setState({
      graph,
      selected: edge,
    }, this.updateParentWithGraph); */
  };

  onUndo = () => {
    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    // Not implemented
    console.warn('Undo is not currently implemented in the example.');
    // Normally any add, remove, or update would record the action in an array.
    // In order to undo it one would simply call the inverse of the action performed. For instance, if someone
    // called onDeleteEdge with (viewEdge, i, edges) then an undelete would be a splicing the original viewEdge
    // into the edges array at position i.
  };

  onCopySelected = () => {
    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    console.warn('copy not supported yet');

    /*
    if (this.state.selected.source) {
      console.warn('Cannot copy selected edges, try selecting a node instead.');

      return;
    }

    const x = this.state.selected.x + 10;
    const y = this.state.selected.y + 10;

    this.setState({
      copiedNode: { ...this.state.selected, x, y },
    }, this.updateParentWithGraph); */
  };

  onPasteSelected = () => {
    /*
    if (!this.state.copiedNode) {
      console.warn(
        'No node is currently in the copy queue. Try selecting a node and copying it with Ctrl/Command-C'
      );
    }

    const graph = this.state.graph;
    const newNode = { ...this.state.copiedNode, id: Date.now() };

    graph.nodes = [...graph.nodes, newNode];
    this.forceUpdate();

    this.updateParentWithGraph(); */
    console.warn('paste not supported yet');
  };

  onTaskInstanceModalSaved = (node: any, wpti: any) => {
    const {
      graph,
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    let {
      savedX,
      savedY
    } = this.state;

    savedX = savedX ?? 200;
    savedY = savedY ?? 200;

    // This is just an example - any sort of logic
    // could be used here to determine node type
    // There is also support for subtypes. (see 'sample' above)
    // The subtype geometry will underlay the 'type' geometry for a node
    const type = 'empty';

    const uuid = wpti.uuid;

    const nodeId = uuid || ('NEW_' + Date.now());

    const viewNode = {
      id: nodeId,
      title: wpti.name,
      type,
      x: savedX,
      y: savedY
    };

    graph.nodes = [...graph.nodes, viewNode];

    if (!uuid) {
      wpti.uuid = nodeId;
    }

    wpti.ui_center_margin_left = savedX;
    wpti.ui_center_margin_top = savedY;

    nodeIdsToWorkflowTaskInstances[nodeId] = wpti;

    this.setState({
      graph,
      nodeIdsToWorkflowTaskInstances,
      workflowTaskInstanceToEdit: null,
      isTaskInstanceEditorOpen: false
    }, this.updateParentWithGraph);
  }


  onTaskInstanceDeleted = (node: any, wpti: any) => {
    console.log('onTaskInstanceDeleted');
    console.dir(node);

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    const nodeId = node['id'];

    if (nodeId) {
      this.removeNode(nodeId);
    }

    this.setState({
      selectedNode: null,
      isTaskInstanceEditorOpen: false
    });
  };

  onTransitionModalSaved = (wt: any) => {
    const {
      graph,
      selectedEdge,
      edgeToWorkflowTransitions
    } = this.state;

    if (!selectedEdge) {
      console.log('No view edge to edit!');
      return;
    }

    selectedEdge.handleText = wt.rule_type;

    const {
      source,
      target
    } = selectedEdge as IEdge;

    const updatedGraph = Object.assign({}, graph);

    wt.from_workflow_task_instance = {
      uuid: source
    };

    wt.to_workflow_task_instance = {
      uuid: target
    };

    const key = WorkflowGraph.computeEdgeKey(selectedEdge);

    edgeToWorkflowTransitions[key] = wt;

    this.setState({
      graph: updatedGraph,
      isTransitionEditorOpen: false,
      selectedEdge: null,
      edgeToWorkflowTransitions,
      selectedNode: selectedEdge
    }, () => {
      this.forceUpdate();
      console.log('forceUpdate done');
      this.updateParentWithGraph();
    });
  }

  onTaskInstanceModalCancelled = () => {
    this.setState({
      isTaskInstanceEditorOpen: false
    });
  }

  onTransitionModalCancelled = () => {
    this.setState({
      isTransitionEditorOpen: false
    });
  }

  onTransitionDeleted = (edge: any | null, wt: any | null) => {
    console.log('onTransitionDeleted');
    console.dir(edge);

    if (edge) {
      this.removeEdge(edge);
    }

    this.setState({
      isTransitionEditorOpen: false
    });
  }

  private updateParentWithGraph() {
    const {
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions
    } = this.state;

    const wptis = _.values(nodeIdsToWorkflowTaskInstances);
    const wts = _.values(edgeToWorkflowTransitions);

    this.props.onGraphChanged(wptis, wts);
  }

  getModalRoot() : HTMLElement {
    const el = document.getElementById('modal-root');

    if (el) {
      return el;
    }

    throw new Error('modal-root element not found');
  }
}
