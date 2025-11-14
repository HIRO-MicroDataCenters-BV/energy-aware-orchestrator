/**
 * Tuning Parameters API models
 * Based on OpenAPI schema from /tuning_parameters/* endpoints
 */

/**
 * Tuning Parameter creation request
 */
export interface TuningParameterCreate {
  output_1: number;
  output_2: number;
  output_3: number;
  alpha: number;
  beta: number;
  gamma: number;
}

/**
 * Tuning Parameter response with database fields
 */
export interface TuningParameterResponse extends TuningParameterCreate {
  id: number;
  created_at: string;
}

/**
 * Tuning Parameter update request
 */
export interface TuningParameterUpdate {
  output_1?: number;
  output_2?: number;
  output_3?: number;
  alpha?: number;
  beta?: number;
  gamma?: number;
}

/**
 * Query parameters for Tuning Parameters list API
 */
export interface TuningParameterQueryParams {
  skip?: number;
  limit?: number;
  start_date?: string;
  end_date?: string;
  [key: string]: unknown;
}

/**
 * Tuning Parameter list response
 */
export interface TuningParameterListResponse {
  items: TuningParameterResponse[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Tuning Parameter statistics
 */
export interface TuningParameterStatistics {
  total_parameters: number;
  avg_output_1: number;
  avg_output_2: number;
  avg_output_3: number;
  avg_alpha: number;
  avg_beta: number;
  avg_gamma: number;
  optimal_ranges: TuningParameterRanges;
}

/**
 * Parameter ranges for validation
 */
export interface TuningParameterRanges {
  output_1: { min: number; max: number };
  output_2: { min: number; max: number };
  output_3: { min: number; max: number };
  alpha: { min: number; max: number };
  beta: { min: number; max: number };
  gamma: { min: number; max: number };
}

/**
 * Parameter comparison result
 */
export interface TuningParameterComparison {
  parameter1: TuningParameterResponse;
  parameter2: TuningParameterResponse;
  differences: TuningParameterDifferences;
  similarity_score: number;
}

/**
 * Differences between two parameters
 */
export interface TuningParameterDifferences {
  output_1: number;
  output_2: number;
  output_3: number;
  alpha: number;
  beta: number;
  gamma: number;
}

/**
 * Parameter trend analysis
 */
export interface TuningParameterTrend {
  date: string;
  avg_output_1: number;
  avg_output_2: number;
  avg_output_3: number;
  avg_alpha: number;
  avg_beta: number;
  avg_gamma: number;
  parameter_count: number;
}

/**
 * Utility functions for tuning parameters
 */

/**
 * Check if parameters are within optimal ranges
 */
export const areParametersOptimal = (
  params: TuningParameterCreate
): boolean => {
  const ranges = getOptimalParameterRange();

  return (
    params.output_1 >= ranges.output_1.min &&
    params.output_1 <= ranges.output_1.max &&
    params.output_2 >= ranges.output_2.min &&
    params.output_2 <= ranges.output_2.max &&
    params.output_3 >= ranges.output_3.min &&
    params.output_3 <= ranges.output_3.max &&
    params.alpha >= ranges.alpha.min &&
    params.alpha <= ranges.alpha.max &&
    params.beta >= ranges.beta.min &&
    params.beta <= ranges.beta.max &&
    params.gamma >= ranges.gamma.min &&
    params.gamma <= ranges.gamma.max
  );
};

/**
 * Calculate similarity between two parameter sets
 */
export const calculateParameterSimilarity = (
  params1: TuningParameterResponse,
  params2: TuningParameterResponse
): number => {
  const diff1 = Math.abs(params1.output_1 - params2.output_1) / 100;
  const diff2 = Math.abs(params1.output_2 - params2.output_2) / 100;
  const diff3 = Math.abs(params1.output_3 - params2.output_3) / 100;
  const diffAlpha = Math.abs(params1.alpha - params2.alpha);
  const diffBeta = Math.abs(params1.beta - params2.beta);
  const diffGamma = Math.abs(params1.gamma - params2.gamma);

  const avgDifference =
    (diff1 + diff2 + diff3 + diffAlpha + diffBeta + diffGamma) / 6;
  return Math.max(0, 1 - avgDifference);
};

/**
 * Calculate differences between two parameter sets
 */
export const calculateParameterDifferences = (
  params1: TuningParameterResponse,
  params2: TuningParameterResponse
): TuningParameterDifferences => {
  return {
    output_1: params2.output_1 - params1.output_1,
    output_2: params2.output_2 - params1.output_2,
    output_3: params2.output_3 - params1.output_3,
    alpha: params2.alpha - params1.alpha,
    beta: params2.beta - params1.beta,
    gamma: params2.gamma - params1.gamma,
  };
};

/**
 * Get optimal parameter ranges
 */
export const getOptimalParameterRange = (): TuningParameterRanges => {
  return {
    output_1: { min: 0, max: 100 },
    output_2: { min: 0, max: 100 },
    output_3: { min: 0, max: 100 },
    alpha: { min: 0, max: 1 },
    beta: { min: 0, max: 1 },
    gamma: { min: 0, max: 1 },
  };
};

/**
 * Validate tuning parameter values
 */
export const validateTuningParameter = (
  params: TuningParameterCreate
): string[] => {
  const errors: string[] = [];
  const ranges = getOptimalParameterRange();

  if (
    params.output_1 < ranges.output_1.min ||
    params.output_1 > ranges.output_1.max
  ) {
    errors.push(
      `output_1 must be between ${ranges.output_1.min} and ${ranges.output_1.max}`
    );
  }

  if (
    params.output_2 < ranges.output_2.min ||
    params.output_2 > ranges.output_2.max
  ) {
    errors.push(
      `output_2 must be between ${ranges.output_2.min} and ${ranges.output_2.max}`
    );
  }

  if (
    params.output_3 < ranges.output_3.min ||
    params.output_3 > ranges.output_3.max
  ) {
    errors.push(
      `output_3 must be between ${ranges.output_3.min} and ${ranges.output_3.max}`
    );
  }

  if (params.alpha < ranges.alpha.min || params.alpha > ranges.alpha.max) {
    errors.push(
      `alpha must be between ${ranges.alpha.min} and ${ranges.alpha.max}`
    );
  }

  if (params.beta < ranges.beta.min || params.beta > ranges.beta.max) {
    errors.push(
      `beta must be between ${ranges.beta.min} and ${ranges.beta.max}`
    );
  }

  if (params.gamma < ranges.gamma.min || params.gamma > ranges.gamma.max) {
    errors.push(
      `gamma must be between ${ranges.gamma.min} and ${ranges.gamma.max}`
    );
  }

  return errors;
};

/**
 * Type guards
 */
export const isTuningParameterCreate = (
  obj: unknown
): obj is TuningParameterCreate => {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof (obj as TuningParameterCreate).output_1 === 'number' &&
    typeof (obj as TuningParameterCreate).output_2 === 'number' &&
    typeof (obj as TuningParameterCreate).output_3 === 'number' &&
    typeof (obj as TuningParameterCreate).alpha === 'number' &&
    typeof (obj as TuningParameterCreate).beta === 'number' &&
    typeof (obj as TuningParameterCreate).gamma === 'number'
  );
};

export const isTuningParameterResponse = (
  obj: unknown
): obj is TuningParameterResponse => {
  return (
    isTuningParameterCreate(obj) &&
    typeof (obj as TuningParameterResponse).id === 'number' &&
    typeof (obj as TuningParameterResponse).created_at === 'string'
  );
};
