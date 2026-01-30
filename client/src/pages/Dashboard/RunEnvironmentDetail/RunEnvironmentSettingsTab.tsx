import { RunEnvironment } from '../../../types/domain_types';
import RunEnvironmentEditor from '../../../components/RunEnvironmentEditor';

import React from 'react';

interface Props {
  runEnvironment: RunEnvironment;
  onSaveStarted: (runEnvironment: RunEnvironment) => void;
  onSaveSuccess: (runEnvironment: RunEnvironment) => void;
  onSaveError: (ex: unknown, values: any) => void;
}

const RunEnvironmentSettingsTab = (props: Props) => {
  return (
    <RunEnvironmentEditor 
      runEnvironment={props.runEnvironment}
      onSaveStarted={props.onSaveStarted}
      onSaveSuccess={props.onSaveSuccess}
      onSaveError={props.onSaveError} 
      debugMode={true}
    />
  );
};

export default RunEnvironmentSettingsTab;
