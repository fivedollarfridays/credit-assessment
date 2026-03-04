/**
 * Request and response models for the Credit Assessment API.
 */

export interface AccountSummaryOptions {
  totalAccounts: number;
  openAccounts: number;
  closedAccounts?: number;
  negativeAccounts?: number;
  collectionAccounts?: number;
  totalBalance?: number;
  totalCreditLimit?: number;
  monthlyPayments?: number;
}

export class AccountSummary {
  readonly totalAccounts: number;
  readonly openAccounts: number;
  readonly closedAccounts: number;
  readonly negativeAccounts: number;
  readonly collectionAccounts: number;
  readonly totalBalance: number;
  readonly totalCreditLimit: number;
  readonly monthlyPayments: number;

  constructor(opts: AccountSummaryOptions) {
    this.totalAccounts = opts.totalAccounts;
    this.openAccounts = opts.openAccounts;
    this.closedAccounts = opts.closedAccounts ?? 0;
    this.negativeAccounts = opts.negativeAccounts ?? 0;
    this.collectionAccounts = opts.collectionAccounts ?? 0;
    this.totalBalance = opts.totalBalance ?? 0;
    this.totalCreditLimit = opts.totalCreditLimit ?? 0;
    this.monthlyPayments = opts.monthlyPayments ?? 0;
  }

  toDict(): Record<string, unknown> {
    return {
      total_accounts: this.totalAccounts,
      open_accounts: this.openAccounts,
      closed_accounts: this.closedAccounts,
      negative_accounts: this.negativeAccounts,
      collection_accounts: this.collectionAccounts,
      total_balance: this.totalBalance,
      total_credit_limit: this.totalCreditLimit,
      monthly_payments: this.monthlyPayments,
    };
  }
}

export interface CreditProfileOptions {
  currentScore: number;
  scoreBand: string;
  overallUtilization: number;
  accountSummary: AccountSummary;
  paymentHistoryPct: number;
  averageAccountAgeMonths: number;
  negativeItems?: string[];
}

export class CreditProfile {
  readonly currentScore: number;
  readonly scoreBand: string;
  readonly overallUtilization: number;
  readonly accountSummary: AccountSummary;
  readonly paymentHistoryPct: number;
  readonly averageAccountAgeMonths: number;
  readonly negativeItems: string[];

  constructor(opts: CreditProfileOptions) {
    this.currentScore = opts.currentScore;
    this.scoreBand = opts.scoreBand;
    this.overallUtilization = opts.overallUtilization;
    this.accountSummary = opts.accountSummary;
    this.paymentHistoryPct = opts.paymentHistoryPct;
    this.averageAccountAgeMonths = opts.averageAccountAgeMonths;
    this.negativeItems = opts.negativeItems ?? [];
  }

  toDict(): Record<string, unknown> {
    return {
      current_score: this.currentScore,
      score_band: this.scoreBand,
      overall_utilization: this.overallUtilization,
      account_summary: this.accountSummary.toDict(),
      payment_history_pct: this.paymentHistoryPct,
      average_account_age_months: this.averageAccountAgeMonths,
      negative_items: this.negativeItems,
    };
  }
}

export class AssessmentResult {
  readonly barrierSeverity: string;
  readonly readiness: Record<string, unknown>;
  readonly barrierDetails: Record<string, unknown>[];
  readonly thresholds: Record<string, unknown>[];
  readonly disputePathway: Record<string, unknown>;
  readonly eligibility: Record<string, unknown>[];
  readonly disclaimer: string;

  constructor(
    barrierSeverity: string,
    readiness: Record<string, unknown>,
    barrierDetails: Record<string, unknown>[],
    thresholds: Record<string, unknown>[],
    disputePathway: Record<string, unknown>,
    eligibility: Record<string, unknown>[],
    disclaimer: string,
  ) {
    this.barrierSeverity = barrierSeverity;
    this.readiness = readiness;
    this.barrierDetails = barrierDetails;
    this.thresholds = thresholds;
    this.disputePathway = disputePathway;
    this.eligibility = eligibility;
    this.disclaimer = disclaimer;
  }

  get readinessScore(): number {
    return (this.readiness["score"] as number) ?? 0;
  }

  static fromDict(data: Record<string, unknown>): AssessmentResult {
    return new AssessmentResult(
      (data["barrier_severity"] as string) ?? "",
      (data["readiness"] as Record<string, unknown>) ?? {},
      (data["barrier_details"] as Record<string, unknown>[]) ?? [],
      (data["thresholds"] as Record<string, unknown>[]) ?? [],
      (data["dispute_pathway"] as Record<string, unknown>) ?? {},
      (data["eligibility"] as Record<string, unknown>[]) ?? [],
      (data["disclaimer"] as string) ?? "",
    );
  }
}
