/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { useState } from 'react';
import { styled, t, useTheme, SupersetTheme } from '@superset-ui/core';
import {
  Comparator,
  MultipleValueComparators,
  D3_FORMAT_OPTIONS,
  sharedControls,
} from '@superset-ui/chart-controls';
import {
  Select,
  Button,
  Form,
  FormItem,
  InputNumber,
  Col,
  Row,
  type FormProps,
} from '@superset-ui/core/components';
import {
  CellTypes,
  ConditionalFormattingConfig,
  OPERATOR_TYPE,
} from './types';
import SelectControl from '../SelectControl';

// TODO: tangled redefinition that aligns with @superset-ui/plugin-chart-table
// used to be imported but main app shouldn't depend on plugins...
export enum ColorSchemeEnum {
  'Green' = 'Green',
  'Red' = 'Red',
}

const FullWidthInputNumber = styled(InputNumber)`
  width: 100%;
`;

const JustifyEnd = styled.div`
  display: flex;
  justify-content: flex-end;
`;

// Use theme token names instead of hex values to support theme switching
const colorSchemeOptions = (theme: SupersetTheme) => [
  { value: 'colorSuccessBg', label: t('success') },
  { value: 'colorWarningBg', label: t('alert') },
  { value: 'colorErrorBg', label: t('error') },
  { value: theme.colors.success.dark1, label: t('success dark') },
  { value: theme.colors.alert.dark1, label: t('alert dark') },
  { value: theme.colors.error.dark1, label: t('error dark') },
  { value: theme.colors.custom.marine, label: t('marine') },
  { value: theme.colors.custom.citron, label: t('citron') },
  { value: theme.colors.custom.tomato, label: t('tomato') },
  { value: theme.colors.custom.brick, label: t('brick') },
  { value: theme.colors.custom.sunset, label: t('sunset') },
  { value: theme.colors.custom.emerald, label: t('emerald') },
  { value: theme.colors.custom.carmine, label: t('carmine') },
  { value: theme.colors.custom.dodger, label: t('dodger') },
];

const formattingSymbolsOptions = [
  { value: '₹', label: t('₹ (INR)') },
  { value: '$', label: t('$ (USD)') },
  { value: 'INR', label: t('INR') },
  { value: '%', label: t('%') },
];

const operatorOptions = [
  { value: Comparator.None, label: t('None') },
  { value: Comparator.GreaterThan, label: '>' },
  { value: Comparator.LessThan, label: '<' },
  { value: Comparator.GreaterOrEqual, label: '≥' },
  { value: Comparator.LessOrEqual, label: '≤' },
  { value: Comparator.Equal, label: '=' },
  { value: Comparator.NotEqual, label: '≠' },
  { value: Comparator.Between, label: '< x <' },
  { value: Comparator.BetweenOrEqual, label: '≤ x ≤' },
  { value: Comparator.BetweenOrLeftEqual, label: '≤ x <' },
  { value: Comparator.BetweenOrRightEqual, label: '< x ≤' },
];

const operationTypeOptions = [
  { value: OPERATOR_TYPE.ABSOLUTE, label: t('Absolute') },
  { value: OPERATOR_TYPE.PERCENTILE, label: t('Percentile') },
];

const cellTypeOptions = [
  { value: CellTypes.GRADIENT, label: t('Gradient') },
  { value: CellTypes.SOLID, label: t('Solid') },
];

const targetValueValidator =
  (
    compare: (targetValue: number, compareValue: number) => boolean,
    rejectMessage: string,
  ) =>
  (targetValue: number | string) =>
  (_: any, compareValue: number | string) => {
    if (
      !targetValue ||
      !compareValue ||
      compare(Number(targetValue), Number(compareValue))
    ) {
      return Promise.resolve();
    }
    return Promise.reject(new Error(rejectMessage));
  };

const targetValueLeftValidator = targetValueValidator(
  (target: number, val: number) => target > val,
  t('This value should be smaller than the right target value'),
);

const targetValueRightValidator = targetValueValidator(
  (target: number, val: number) => target < val,
  t('This value should be greater than the left target value'),
);

const isOperatorMultiValue = (operator?: Comparator) =>
  operator && MultipleValueComparators.includes(operator);

const isOperatorNone = (operator?: Comparator) =>
  !operator || operator === Comparator.None;

const rulesRequired = [{ required: true, message: t('Required') }];

type GetFieldValue = Pick<Required<FormProps>['form'], 'getFieldValue'>;
const rulesTargetValueLeft = [
  { required: true, message: t('Required') },
  ({ getFieldValue }: GetFieldValue) => ({
    validator: targetValueLeftValidator(getFieldValue('targetValueRight')),
  }),
];

const rulesTargetValueRight = [
  { required: true, message: t('Required') },
  ({ getFieldValue }: GetFieldValue) => ({
    validator: targetValueRightValidator(getFieldValue('targetValueLeft')),
  }),
];

const targetValueLeftDeps = ['targetValueRight'];
const targetValueRightDeps = ['targetValueLeft'];

const shouldFormItemUpdate = (
  prevValues: ConditionalFormattingConfig,
  currentValues: ConditionalFormattingConfig,
) =>
  isOperatorNone(prevValues.operator) !==
    isOperatorNone(currentValues.operator) ||
  isOperatorMultiValue(prevValues.operator) !==
    isOperatorMultiValue(currentValues.operator);

const renderOperator = ({ showOnlyNone }: { showOnlyNone?: boolean } = {}) => (
  <FormItem
    name="operator"
    label={t('Operator')}
    rules={rulesRequired}
    initialValue={operatorOptions[0].value}
  >
    <Select
      ariaLabel={t('Operator')}
      options={showOnlyNone ? [operatorOptions[0]] : operatorOptions}
    />
  </FormItem>
);

const operationType = (
  <FormItem
    name="operationType"
    label={t('Operation Type')}
    rules={rulesRequired}
    initialValue={operationTypeOptions[0].value}
  >
    <Select ariaLabel={t('Operation Type')} options={operationTypeOptions} />
  </FormItem>
);

const cellType = (
  <FormItem
    name="cellType"
    label={t('Cell Type')}
    rules={rulesRequired}
    initialValue={cellTypeOptions[0].value}
  >
    <Select ariaLabel={t('Cell Type')} options={cellTypeOptions} />
  </FormItem>
);

const renderOperatorFields = ({ getFieldValue }: GetFieldValue) =>
  isOperatorNone(getFieldValue('operator')) ? (
    <Row gutter={12}>
      <Col span={6}>{renderOperator()}</Col>
    </Row>
  ) : isOperatorMultiValue(getFieldValue('operator')) ? (
    <Row gutter={12}>
      <Col span={9}>
        <FormItem
          name="targetValueLeft"
          label={t('Left value')}
          rules={rulesTargetValueLeft}
          dependencies={targetValueLeftDeps}
          validateTrigger="onBlur"
          trigger="onBlur"
        >
          <FullWidthInputNumber />
        </FormItem>
      </Col>
      <Col span={6}>{renderOperator()}</Col>
      <Col span={9}>
        <FormItem
          name="targetValueRight"
          label={t('Right value')}
          rules={rulesTargetValueRight}
          dependencies={targetValueRightDeps}
          validateTrigger="onBlur"
          trigger="onBlur"
        >
          <FullWidthInputNumber />
        </FormItem>
      </Col>
    </Row>
  ) : (
    <>
      <Row gutter={12}>
        <Col span={6}>{renderOperator()}</Col>
        <Col span={14}>
          <FormItem
            name="targetValue"
            label={t('Target value')}
            rules={rulesRequired}
          >
            <FullWidthInputNumber />
          </FormItem>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={10}>{operationType}</Col>
        <Col span={10}>{cellType}</Col>
      </Row>
    </>
  );

export const FormattingPopoverContent = ({
  config,
  onChange,
  columns = [],
  extraColorChoices = [],
  hasOperator = true,
  isD3ValueFormatting,
}: {
  config?: ConditionalFormattingConfig;
  onChange: (config: ConditionalFormattingConfig) => void;
  columns: { label: string; value: string }[];
  extraColorChoices?: { label: string; value: string }[];
  hasOperator?: boolean;
  isD3ValueFormatting?: boolean;
}) => {
  const theme = useTheme();
  const colorScheme = colorSchemeOptions(theme);
  const [showOperatorFields, setShowOperatorFields] = useState(
    config === undefined ||
      (config?.colorScheme !== ColorSchemeEnum.Green &&
        config?.colorScheme !== ColorSchemeEnum.Red),
  );
  const handleChange = (event: any) => {
    setShowOperatorFields(
      !(event === ColorSchemeEnum.Green || event === ColorSchemeEnum.Red),
    );
  };

  return (
    <Form
      onFinish={onChange}
      initialValues={config}
      requiredMark="optional"
      layout="vertical"
    >
      <Row gutter={12}>
        <Col span={12}>
          <FormItem
            name="column"
            label={t('Column')}
            rules={rulesRequired}
            initialValue={columns[0]?.value}
          >
            <Select ariaLabel={t('Select column')} options={columns} />
          </FormItem>
        </Col>
        {hasOperator ? (
          <Col span={12}>
            <FormItem
              name="colorScheme"
              label={t('Color scheme')}
              rules={rulesRequired}
              initialValue={colorScheme[0].value}
            >
              <Select
                onChange={event => handleChange(event)}
                ariaLabel={t('Color scheme')}
                options={[...colorScheme, ...extraColorChoices]}
              />
            </FormItem>
          </Col>
        ) : isD3ValueFormatting ? (
          <Col span={12}>
            <FormItem
              name="d3ValueFormatting"
              rules={rulesRequired}
              initialValue={D3_FORMAT_OPTIONS[0][0]}
            >
              <SelectControl
                {...sharedControls.y_axis_format}
                label={t('Value Format')}
              />
            </FormItem>
          </Col>
        ) : (
          <Col span={12}>
            <FormItem
              name="addSymbols"
              label={t('Add Symbols')}
              rules={rulesRequired}
              initialValue={formattingSymbolsOptions[0].value}
            >
              <Select
                ariaLabel={t('Add Symbols')}
                options={formattingSymbolsOptions}
              />
            </FormItem>
          </Col>
        )}
      </Row>
      <FormItem noStyle shouldUpdate={shouldFormItemUpdate}>
        {hasOperator ? (
          showOperatorFields ? (
            renderOperatorFields
          ) : (
            <Row gutter={12}>
              <Col span={6}>{renderOperator({ showOnlyNone: true })}</Col>
            </Row>
          )
        ) : null}
      </FormItem>
      <FormItem>
        <JustifyEnd>
          <Button htmlType="submit" buttonStyle="primary">
            {t('Apply')}
          </Button>
        </JustifyEnd>
      </FormItem>
    </Form>
  );
};
