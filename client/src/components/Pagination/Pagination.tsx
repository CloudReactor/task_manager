import React from "react";
import UltimatePagination from 'react-ultimate-pagination-bootstrap-4';

import Form from 'react-bootstrap/Form'
import styles from './Pagination.module.scss';

interface Props {
  currentPage: number;
  pageSize: number;
  count: number;
  handleClick: (currentPage: number) => void;
  handleSelectItemsPerPage: (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => void;
  itemsPerPageOptions: any[];
}

const DefaultPagination = ({
  currentPage,
  pageSize,
  count,
  handleClick,
  handleSelectItemsPerPage,
  itemsPerPageOptions
}: Props) => (
  <div className="d-flex justify-content-between mt-4">
    <UltimatePagination
      onChange={(page: number) => handleClick(page - 1)}
      currentPage={currentPage + 1}
      totalPages={Math.floor(count / pageSize) + 1}
    />
    <div className={styles.showSelect}>
      <div>Show</div>
      <Form.Control as="select"
       onChange={handleSelectItemsPerPage} value={pageSize} size="sm">
        {itemsPerPageOptions.map((option: { value: number }) => (
          <option key={option.value} value={option.value}>
            {option.value}
          </option>
        ))}
      </Form.Control>
      <div>per page</div>
    </div>
  </div>
);

export default DefaultPagination;
