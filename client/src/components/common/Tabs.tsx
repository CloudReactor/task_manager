import React from 'react';
import Nav from 'react-bootstrap/Nav';
import classNames from 'classnames';
import styles from './TabsStyle.module.scss';

interface Props {
  selectedTab: string;
  navItems: any;
  onTabChange: (selectedKey: string) => void;
}
  
const Tabs = ({ selectedTab, onTabChange, navItems }: Props) =>  {

	return (
    <div className={styles.tabBar}>
      <Nav as="ul" className={styles.tabFix} onSelect={(selectedKey) => onTabChange(selectedKey || '')}>
        {
          navItems.map((item: any) => {
            return (
              <Nav.Item
                key={item}
                as="li"
                className={classNames({
                  [styles.tabsNavItem]: true,
                  [styles.tabsNavSelected]: (selectedTab === item.toLowerCase()),
                })}
              >
                <Nav.Link eventKey={item}>{item}</Nav.Link>
              </Nav.Item>
            );
          })
        }
      </Nav>
    </div>
	);
}

export default Tabs;