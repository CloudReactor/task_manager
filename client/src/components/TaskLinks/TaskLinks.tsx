import React from "react";
import { ExternalLink } from "../../types/domain_types";
import styles from './styles.module.scss'

interface Props {
  links: ExternalLink[];
}

const TaskLinks = ({ links }: Props) => {
  return (
    <div className={styles.links}>
    {
      links.map(link => {
        const linkContents = link.icon_url ?
          <img src={link.icon_url} alt={link.name} /> :
          <span>{link.name}</span>;

        return (
          <a
            key={link.name}
            className={styles.externalLink}
            href={link.link_url}
            target="_blank"
            rel="noopener noreferrer"
            title={link.name}
          >
            { linkContents }
          </a>
        );
      })      
    }
    </div>
  );
};

export default TaskLinks;
