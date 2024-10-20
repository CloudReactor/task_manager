import React from 'react';
import { Link as RouterLink } from "react-router-dom";

import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import styles from './BreadcrumbBar.module.scss';

interface Props {
  rootUrl?: string,
  rootLabel?: string,
	firstLevel: any;
  secondLevel?: any;
}

const BreadcrumbBar = ({ rootUrl, rootLabel, firstLevel, secondLevel }: Props) => {

	return (
    <Breadcrumbs separator="›" aria-label="breadcrumb" className={styles.breadcrumb}>
      <Link component={RouterLink} to={rootUrl || '/'}>
        { rootLabel || 'Dashboard' }
      </Link>
      <div>
          {firstLevel}
      </div>
      { secondLevel
        ? <div>
            {secondLevel}
          </div>
        : null
      }
    </Breadcrumbs>
	);
}

export default BreadcrumbBar;