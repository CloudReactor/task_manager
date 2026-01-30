import {
  RunEnvironment
} from '../../../types/domain_types';

import {
  fetchRunEnvironment,
  cloneRunEnvironment,
  deleteRunEnvironment
} from '../../../utils/api';

import React, { Fragment, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { makeEntityDetailComponent, EntityDetailInnerProps } from '../../../components/common/EntityDetailHoc'

import RunEnvironmentSettingsTab from './RunEnvironmentSettingsTab';
import RunEnvironmentEventsTab from './RunEnvironmentEventsTab';
import Tabs from '../../../components/common/Tabs';

interface Props {
}

const RunEnvironmentDetail = makeEntityDetailComponent<RunEnvironment, Props>(
  (props: EntityDetailInnerProps<RunEnvironment>) => {
    const [searchParams, setSearchParams] = useSearchParams();
    const tab = searchParams.get('tab')?.toLowerCase() || 'settings';
    const [selectedTab, setSelectedTab] = useState(tab);

    const handleTabChange = (newTab: string) => {
      const lowerTab = newTab.toLowerCase();
      setSelectedTab(lowerTab);
      setSearchParams({ tab: lowerTab });
    };

    const navItems = ['Settings', 'Events'];

    if (!props.entity) {
      return null;
    }

    return (
      <Fragment>
        <Tabs selectedTab={selectedTab} navItems={navItems} onTabChange={handleTabChange} />
        <div>
          {(() => {
            switch (selectedTab) {
              case 'events':
                return <RunEnvironmentEventsTab runEnvironment={props.entity} />;
              case 'settings':
              default:
                return (
                  <RunEnvironmentSettingsTab 
                    runEnvironment={props.entity}
                    onSaveStarted={props.onSaveStarted}
                    onSaveSuccess={props.onSaveSuccess}
                    onSaveError={props.onSaveError}
                  />
                );
            }
          })()}
        </div>
      </Fragment>
    );
  }, {
    entityName: 'Run Environment',
    fetchEntity: fetchRunEnvironment,
    cloneEntity: cloneRunEnvironment,
    deleteEntity: deleteRunEnvironment
  }
);

export default RunEnvironmentDetail;
