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
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import {
  toggleExpandSlice,
  setFocusedFilterField,
  unsetFocusedFilterField,
} from 'src/dashboard/actions/dashboardState';
import { updateComponents } from 'src/dashboard/actions/dashboardLayout';
import { changeFilter } from 'src/dashboard/actions/dashboardFilters';
import {
  addSuccessToast,
  addDangerToast,
} from 'src/components/MessageToasts/actions';
import { refreshChart } from 'src/components/Chart/chartAction';
import { logEvent } from 'src/logger/actions';
import {
  getActiveFilters,
  getAppliedFilterValues,
} from 'src/dashboard/util/activeDashboardFilters';
import getFormDataWithExtraFilters from 'src/dashboard/util/charts/getFormDataWithExtraFilters';
import Chart from 'src/dashboard/components/gridComponents/Chart';
import { PLACEHOLDER_DATASOURCE } from 'src/dashboard/constants';
import { cloneDeep, isEmpty } from 'lodash';

const EMPTY_OBJECT = {};

function mapStateToProps(
  {
    charts: chartQueries,
    dashboardInfo,
    dashboardState,
    dataMask,
    datasources,
    sliceEntities,
    nativeFilters,
    common,
    dashboardLayout,
  },
  ownProps,
) {
  const { id, extraControls, setControlValue, componentId } = ownProps;

  const { mergedPivotTables = [] } = dashboardLayout.present || {};

  let mutationNeeded = false;
  let mutatedChart = cloneDeep(chartQueries[id]);

  const mergedTables = mergedPivotTables.find(arr => arr.includes(componentId));

  let mergedCharts = mergedTables?.map(
    chart => dashboardLayout.present?.[chart]?.meta?.chartId,
  );

  if (
    !isEmpty(mergedTables) &&
    dashboardLayout.present?.[mergedTables[0]] &&
    mergedCharts.includes(id)
  ) {
    mutationNeeded = true;

    let colNames = [];
    let combinedData = [];
    let combinedMap = new Map();
    let mutated_label_map = {};
    let mergedColTypes = [];
    let colNameSet = new Set();
    let colTypeDict = {};
    let indexNames = [];

    mergedTables.forEach(table => {
      const chartId = dashboardLayout.present?.[table]?.meta?.chartId;
      const {
        colnames = [],
        data = [],
        label_map = {},
        coltypes = [],
        indexnames = [],
      } = chartQueries[chartId].queriesResponse?.[0] || {};

      mutated_label_map = { ...mutated_label_map, ...label_map };

      colnames.forEach(col => {
        if (!colNames.includes(col)) {
          colNames.push(col);
          indexNames = [...indexNames, indexNames.length];
        }
      });

      let tableMetricRows = [];
      data.forEach(item => {
        const item_id = item[colNames[0]];
        if (combinedMap.has(item_id)) {
          // Merge existing item in combinedMap
          let existingItem = combinedMap.get(item_id);
          combinedMap.set(item_id, { ...existingItem, ...item });
        } else {
          // Add new item to combinedMap
          combinedMap.set(item_id, item);
        }
      });

      // Convert map back to array
      combinedData = Array.from(combinedMap.values());

      colNames.forEach((colName, i) => {
        if (!colNameSet.has(colName)) {
          colNameSet.add(colName);
          colTypeDict[colName] = coltypes[i] || 0;
        }
      });
    });

    mergedColTypes = colNames.map(colName => colTypeDict[colName]);

    ((mutatedChart.queriesResponse || [])[0] || {}).data = combinedData;
    ((mutatedChart.queriesResponse || [])[0] || {}).colnames = colNames;
    ((mutatedChart.queriesResponse || [])[0] || {}).label_map =
      mutated_label_map;
    ((mutatedChart.queriesResponse || [])[0] || {}).coltypes =
      mergedColTypes || [];
    ((mutatedChart.queriesResponse || [])[0] || {}).indexnames =
      indexNames || [];
    ((mutatedChart.queriesResponse || [])[0] || {}).rowcount =
      indexNames.length;
    ((mutatedChart.queriesResponse || [])[0] || {}).sql_rowcount =
      indexNames.length;

//     let mergedMetrics = mergedCharts?.map(
//       chart => chartQueries?.[chart]?.form_data?.metrics,
//     );
//     mergedMetrics = mergedMetrics.flat();

   // mutatedChart.form_data.metrics = mergedMetrics;

    //* check to maintain the order...
    mutatedChart.form_data.colOrder = 'none';
    mutatedChart.form_data.rowOrder = 'none';
  }

  const chart = mutationNeeded
    ? mutatedChart || EMPTY_OBJECT
    : chartQueries[id] || EMPTY_OBJECT;
  mutationNeeded = false;

  const datasource =
    (chart && chart.form_data && datasources[chart.form_data.datasource]) ||
    PLACEHOLDER_DATASOURCE;
  const { colorScheme, colorNamespace, datasetsStatus } = dashboardState;
  const labelColors = dashboardInfo?.metadata?.label_colors || {};
  const sharedLabelColors = dashboardInfo?.metadata?.shared_label_colors || {};

  const formData = getFormDataWithExtraFilters({
    chart,
    chartConfiguration: dashboardInfo.metadata?.chart_configuration,
    charts: chartQueries,
    filters: getAppliedFilterValues(id),
    colorScheme,
    colorNamespace,
    sliceId: id,
    nativeFilters: nativeFilters?.filters,
    allSliceIds: dashboardState.sliceIds,
    dataMask,
    extraControls,
    labelColors,
    sharedLabelColors,
  });

  formData.dashboardId = dashboardInfo.id;

  return {
    chart,
    datasource,
    labelColors,
    sharedLabelColors,
    slice: sliceEntities.slices[id],
    timeout: dashboardInfo.common.conf.SUPERSET_WEBSERVER_TIMEOUT,
    filters: getActiveFilters() || EMPTY_OBJECT,
    formData,
    editMode: dashboardState.editMode,
    isExpanded: !!dashboardState.expandedSlices[id],
    supersetCanExplore: !!dashboardInfo.superset_can_explore,
    supersetCanShare: !!dashboardInfo.superset_can_share,
    supersetCanCSV: !!dashboardInfo.superset_can_csv,
    ownState: dataMask[id]?.ownState,
    filterState: dataMask[id]?.filterState,
    maxRows: common.conf.SQL_MAX_ROW,
    setControlValue,
    datasetsStatus,
    emitCrossFilters: !!dashboardInfo.crossFiltersEnabled,
    mergedPivotTables,
  };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      updateComponents,
      addSuccessToast,
      addDangerToast,
      toggleExpandSlice,
      changeFilter,
      setFocusedFilterField,
      unsetFocusedFilterField,
      refreshChart,
      logEvent,
    },
    dispatch,
  );
}

export default connect(mapStateToProps, mapDispatchToProps)(Chart);
