import React, { Fragment } from 'react';
import { Field } from 'formik';
import CustomInput from './CustomInput';
import styles from './SettingsForm.module.scss';

interface Props {
  items: any;
  onChange?: any;
  onBlur?: any;
}

export const SettingsForm = (props: Props) => {
  const {
    items,
    onChange,
    onBlur
  } = props || {};

  return items?.map((item: any, i: any) => {
    const {
      title,
      controls
    } = item || {};

    return (
      <div
        className={styles.formSection}
        key={`form-container-${i}`}
      >
        {
          title &&
            <div
              key={`form-section-${i}`}
              className={styles.sectionTitle}
            >
              {title}
            </div>
        }
        <div>
          {controls?.map((control: any, j: number) => {
            return (
              <Fragment key={`control-${title}-element-${j}`}>
                <Field
                  {...control}
                  component={CustomInput}
                  onChange={onChange}
                  onBlur={onBlur}>
                </Field>
              </Fragment>
            );
          })}
        </div>
      </div>
    );
  })
}

export default SettingsForm;
