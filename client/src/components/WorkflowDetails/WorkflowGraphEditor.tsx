import _ from 'lodash';

import * as C from '../../utils/constants';

import {
  Workflow,
  WorkflowTaskInstance,
  WorkflowTransition,
  WorkflowExecution
} from "../../types/domain_types";

import React, { Component, Fragment }  from 'react';
import ReactDOM from 'react-dom';

import {
  GlobalContext,
  accessLevelForCurrentGroup
} from '../../context/GlobalContext';

import WorkflowTaskInstanceEditor from './WorkflowTaskInstanceEditor';
import WorkflowTransitionEditor from './WorkflowTransitionEditor';

import {
  GraphView,
  IGraphInput,
  IEdge,
  INode,
  GraphUtils
} from 'react-digraph';

import * as WorkflowGraph from '../../utils/workflow_graph';

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
  selected: any;
  lastSelectionAt: number | null;
  workflowTaskInstanceToEdit: any;
  isTaskInstanceEditorOpen: boolean;
  workflowTransitionToEdit: any;
  isTransitionEditorOpen: boolean;
  viewEdgeToEdit: IEdge | null;
  savedX: number | null;
  savedY: number | null;
  nodeIdsToWorkflowTaskInstances: any;
  edgeToWorkflowTransitions: any;
  modalDiv: any;
}

const DOUBLE_CLICK_DELAY_MILLIS = 500;

export default class WorkflowGraphEditor extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    const [
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions
    ] = WorkflowGraph.makeGraph(props.workflow, props.workflowExecution);

    this.state = {
      graph,
      selected: {},
      lastSelectionAt: null,
      copiedNode: null,
      workflowTaskInstanceToEdit: null,
      isTaskInstanceEditorOpen: false,
      workflowTransitionToEdit: null,
      isTransitionEditorOpen: false,
      viewEdgeToEdit: null,
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
      selected,
      workflowTaskInstanceToEdit,
      isTaskInstanceEditorOpen,
      workflowTransitionToEdit,
      isTransitionEditorOpen,
      modalDiv
    } = this.state;

    console.log('WorkflowGraphEditor rendering');

    const nodes = graph.nodes;
    const edges = graph.edges;

    const NodeTypes = WorkflowGraph.GraphConfig.NodeTypes;
    const NodeSubtypes = WorkflowGraph.GraphConfig.NodeSubtypes;
    const EdgeTypes = WorkflowGraph.GraphConfig.EdgeTypes;

    return (
      <div>
        <div id='graph' className="graph-view">
          <GraphView  ref='GraphView'
                      nodeKey={WorkflowGraph.NODE_KEY}
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
                      readOnly={readOnly}
                      onSelectNode={this.onSelectNode}
                      onCreateNode={this.onCreateNode}
                      onUpdateNode={this.onUpdateNode}
                      onDeleteNode={this.onDeleteNode}
                      onSelectEdge={this.onSelectEdge}
                      onCreateEdge={this.onCreateEdge}
                      onSwapEdge={this.onSwapEdge}
                      onDeleteEdge={this.onDeleteEdge}
                      onUndo={this.onUndo}
                      zoomDelay={0}
                      zoomDur={500} />
        </div>

        {
          ReactDOM.createPortal(
            <Fragment>
              <WorkflowTaskInstanceEditor workflowTaskInstance={workflowTaskInstanceToEdit}
               runEnvironmentUuid={runEnvironmentUuid}
               isOpen={isTaskInstanceEditorOpen}
               onSave={this.onTaskInstanceModalSaved}
               onCancel={this.onTaskInstanceModalCancelled} />

              <WorkflowTransitionEditor workflowTransition={workflowTransitionToEdit}
               isOpen={isTransitionEditorOpen}
               onSave={this.onTransitionModalSaved}
               onCancel={this.onTransitionModalCancelled} />
            </Fragment>,
            modalDiv
          )
        }
      </div>
    );
  }

  renderNodeText = (data: any, id: string | number, isSelected: boolean) => {
    //const title = data.title;
    let title = data.title;
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

  onSelectNode = (viewNode: INode | null) => {
    console.log('onSelectNode');

    const {
      selected,
      lastSelectionAt,
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    let {
      workflowTaskInstanceToEdit,
      isTaskInstanceEditorOpen,
      savedX,
      savedY
    } = this.state;

    const now = new Date().getTime();

    if (viewNode && selected && (selected.id === viewNode.id) &&
        lastSelectionAt && (lastSelectionAt + DOUBLE_CLICK_DELAY_MILLIS > now )) {
      console.log('Double click of node');

      workflowTaskInstanceToEdit = nodeIdsToWorkflowTaskInstances[viewNode.id];
      isTaskInstanceEditorOpen = true;
      savedX = viewNode.x || 0;
      savedY = viewNode.y|| 0;
      console.log('wti to edit = ');
      console.dir(workflowTaskInstanceToEdit);
    }

    // Deselect events will send Null viewNode
    this.setState({
      selected: viewNode,
      lastSelectionAt: now,
      workflowTaskInstanceToEdit,
      isTaskInstanceEditorOpen,
      savedX,
      savedY
    });
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

  onDeleteNode = (viewNode: INode, nodeId: string, nodeArr: INode[]) => {
    console.log(`onDeleteNode, nodeId = ${nodeId}`);

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

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

    graph.nodes = nodeArr;
    graph.edges = newEdges;

    this.setState({
      graph,
      nodeIdsToWorkflowTaskInstances,
      edgeToWorkflowTransitions,
      selected: null
    }, this.updateParentWithGraph);
  }

  onSelectEdge = (viewEdge: IEdge) => {
    console.log('onSelectEdge');

    const {
      selected,
      lastSelectionAt,
      edgeToWorkflowTransitions
    } = this.state;

    let {
      workflowTransitionToEdit,
      isTransitionEditorOpen,
      viewEdgeToEdit
    } = this.state;

    const now = new Date().getTime();
    const viewEdgeKey = viewEdge ? WorkflowGraph.computeEdgeKey(viewEdge) : '';
    const selectedEdgeKey = selected ? WorkflowGraph.computeEdgeKey(selected) : '';

    console.log(`VEK = '${viewEdgeKey}', SEK = '${selectedEdgeKey}'`);

    if (viewEdge && (selectedEdgeKey === viewEdgeKey) &&
        lastSelectionAt && (lastSelectionAt + DOUBLE_CLICK_DELAY_MILLIS > now )) {
       console.log('Double click of edge');

       workflowTransitionToEdit = edgeToWorkflowTransitions[viewEdgeKey];
       isTransitionEditorOpen = true;
       viewEdgeToEdit = viewEdge;
    }

    this.setState({
      selected: viewEdge,
      lastSelectionAt: now,
      workflowTransitionToEdit,
      isTransitionEditorOpen,
      viewEdgeToEdit
    });
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

    const viewEdgeToEdit = {
      source,
      target,
      type,
      handleText: '[pending]'

    };

    const {
      graph
    } = this.state;

    graph.edges = [...graph.edges, viewEdgeToEdit];

    this.setState({
      isTransitionEditorOpen: true,
      viewEdgeToEdit,
      selected: viewEdgeToEdit
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

  // Called when an edge is deleted
  onDeleteEdge = (viewEdge: IEdge, edges: IEdge[]) => {
    console.log('onDeleteEdge');

    const accessLevel = accessLevelForCurrentGroup(this.context);
    if (!accessLevel || (accessLevel < C.ACCESS_LEVEL_DEVELOPER)) {
      return;
    }

    const {
      graph,
      edgeToWorkflowTransitions
    } = this.state;

    graph.edges = edges;

    const edgeKey = WorkflowGraph.computeEdgeKey(viewEdge);
    delete edgeToWorkflowTransitions[edgeKey];

    this.setState({
      graph,
      edgeToWorkflowTransitions,
      selected: null,
    }, this.updateParentWithGraph);
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

  onTaskInstanceModalSaved = (wpti: any) => {
    const {
      graph,
      nodeIdsToWorkflowTaskInstances
    } = this.state;

    let {
      savedX,
      savedY
    } = this.state;

    savedX = savedX || 200;
    savedY = savedY || 200;

    // This is just an example - any sort of logic
    // could be used here to determine node type
    // There is also support for subtypes. (see 'sample' above)
    // The subtype geometry will underlay the 'type' geometry for a node
    const type = 'empty';

    const uuid = wpti['uuid'];

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

  onTransitionModalSaved = (wt: any) => {
    const {
      graph,
      viewEdgeToEdit,
      edgeToWorkflowTransitions
    } = this.state;

    if (!viewEdgeToEdit) {
      console.log('No view edge to edit!');
      return;
    }

    viewEdgeToEdit.handleText = wt.rule_type;

    const {
      source,
      target
    } = viewEdgeToEdit as IEdge;

    const updatedGraph = Object.assign({}, graph);

    wt.from_workflow_task_instance = {
      uuid: source
    };

    wt.to_workflow_task_instance = {
      uuid: target
    };

    const key = WorkflowGraph.computeEdgeKey(viewEdgeToEdit);

    edgeToWorkflowTransitions[key] = wt;

    this.setState({
      graph: updatedGraph,
      isTransitionEditorOpen: false,
      viewEdgeToEdit: null,
      edgeToWorkflowTransitions,
      selected: viewEdgeToEdit
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
