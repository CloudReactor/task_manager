import { ApiKey } from '../../../types/domain_types';

import {
  makeEmptyResultsPage,
  ResultsPage,
  fetchApiKeys
} from "../../../utils/api";

import React, { useContext, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import classNames from 'classnames';

import { GlobalContext } from '../../../context/GlobalContext';
import cancelTokenHoc, { CancelTokenProps } from '../../../hocs/cancelTokenHoc';

import { API_KEYS } from '../../../constants/routes';
import CustomButton from '../../common/Button/CustomButton';
import styles from './Onboarding.module.scss';

interface Props {
}

type InnerProps = Props & CancelTokenProps;

const Onboarding = (props: InnerProps) => {
  const [keyList, setKeyList] = useState<ResultsPage<ApiKey>>(
    makeEmptyResultsPage());

  const { cancelToken } = props;
  const { currentGroup } = useContext(GlobalContext);

  useEffect(() => {
    const fetchKeys = async () => {

      // fetch just a single API key
      const result = await fetchApiKeys({
        groupId: currentGroup?.id,
        maxResults: 1,
        cancelToken
      });
      setKeyList(result);
    }
    fetchKeys();
  }, [currentGroup, cancelToken]);

  const key = keyList && keyList.results && keyList.results[0] ? keyList.results[0].key : null;

  return (
    <div className={styles.container}>
      <div className={classNames({
        [styles.frame]: true,
        'dp12': true,
      })}>
        <h1>Welcome!</h1>
        <div className={styles.content}>
          <div className={styles.para}>
            CloudReactor makes it easy for you to deploy tasks to AWS — and to monitor, manage and orchestrate them from a single dashboard.
          </div>
          <hr />
          <div className={styles.para}>
            The getting started guide will walk you through everything you need to start using CloudReactor. You&apos;ll need:
          </div>
          <div className={classNames({
            [styles.para]: true,
            [styles.bulletRow]: true,
          })}>
            <div>
              <i className={'fa fa-chevron-right pl-3 pr-3'} />
            </div>
            <div>
              Your AWS credentials. This should have admin privileges, since you&apos;ll be setting up an ECS cluster to run tasks.
            </div>
          </div>
          <div className={classNames({
            [styles.para]: true,
            [styles.bulletRow]: true,
          })}>
            <div>
              <i className={'fa fa-chevron-right pl-3 pr-3'} />
            </div>
            {
              (key === null)
              ? <div>
                  <div>A CloudReactor API key.{' '}
                    <Link to={API_KEYS}>Create one here</Link>.
                  </div>
                </div>
              : <div>
                  <div>Your CloudReactor API key:</div>
                  <div className={styles.apiKey}>{key}</div>
                </div>
            }
          </div>
        </div>
        <CustomButton
          className="noMargin"
          fullWidth
          label="Take me to the getting started guide!"
          component="div"
          href="https://docs.cloudreactor.io"
        />
      </div>
    </div>
  );
}

export default cancelTokenHoc(Onboarding);
