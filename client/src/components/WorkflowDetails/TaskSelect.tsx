import React, { Component }  from 'react';

import {EntityReference, Task} from '../../types/domain_types';

import { fetchTasks } from '../../utils/api';

import { GlobalContext } from '../../context/GlobalContext';

interface Field {
  onChange: (event: any) => void;
  onBlur: () => void;
  name: string;
  value: string | null;
}

interface Props {
  field: Field;
  form: any;
}

interface State {
  tasks: EntityReference[] | null;
  selectedTaskUuid: string;
}

export default class TaskSelect extends Component<Props, State> {
  static contextType = GlobalContext;

  constructor(props: Props) {
    super(props);

    const {
      field
    } = this.props;

    this.state = {
      tasks: null,
      selectedTaskUuid: field.value || ''
    };
  }

  async componentDidMount() {
    await this.fetchData();
  }

  public render() {
    const {
      field
    } = this.props;

    const {
      tasks,
      selectedTaskUuid
    } = this.state;

    //debugger;

    //console.dir(field);

    const options: any[] = tasks ? tasks.map(task => {
      return {
        text: task.name,
        value: task.uuid
      };
    }) : [];

    //debugger;

    //console.dir(options);

    return (
      <select name="selectedTaskUuid" value={selectedTaskUuid || ''}
       className="form-control" onChange={this.handleChange}>
        <option value="" key="">Select a Task</option>
        {
          options.map((opt, i, arr) => {
            return (
              <option value={opt.value} key={opt.value}>
                {opt.text}
              </option>
            );
          })
        }
      </select>
    );
  }

  handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    console.log('On change');
    //debugger;

    const selectedTaskUuid = event.target.value;

    console.log(`Selected Task UUID = ${selectedTaskUuid}`);

    event.persist();

    this.setState({
      selectedTaskUuid
    }, () => {
      console.log('handleChange post setState() callback');
      const {
        field
      } = this.props;

      //debugger;
      field.onChange(event);
    });
  }

  async fetchData() {
    const pageSize = 100;
    let allResults: Task[] = [];
    let offset = 0;
    let done = false;

    const { currentGroup } = this.context;

    while (!done) {
      const page = await fetchTasks({
        sortBy: 'name',
        offset,
        maxResults: pageSize,
        groupId: currentGroup?.id
      });
      allResults = allResults.concat(page.results);

      done = page.results.length < pageSize;
      offset += pageSize;
    }

    this.setState({
      tasks: allResults
    });
  }
}
