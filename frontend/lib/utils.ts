import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { ExecutionStage, ApprovalStatus, PaymentStatus } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(amount: number | null | undefined): string {
  if (amount == null || isNaN(amount)) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  try {
    const d = new Date(dateString);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

export function getStageLabel(stage: ExecutionStage | string): string {
  switch (stage) {
    case 'REQUEST_CREATED':
      return 'Request Created';
    case 'PARSING':
      return 'Understanding Request';
    case 'DISCOVERING':
      return 'Finding Offers';
    case 'NEGOTIATING':
      return 'Negotiating with Suppliers';
    case 'POLICY_CHECK':
      return 'Validating Financial Policy';
    case 'APPROVAL_REQUIRED':
      return 'Waiting for Approval';
    case 'READY_FOR_PAYMENT':
      return 'Payment Authorized';
    case 'PAYMENT_PENDING':
      return 'Waiting for Payment';
    case 'PAID':
      return 'Payment Confirmed';
    case 'COMPLETED':
      return 'Procurement Completed';
    case 'FAILED':
      return 'Procurement Failed';
    case 'CANCELLED':
      return 'Request Cancelled';
    default:
      return stage;
  }
}

export function getStageBadgeColor(stage: ExecutionStage | string): string {
  switch (stage) {
    case 'COMPLETED':
    case 'PAID':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    case 'APPROVAL_REQUIRED':
      return 'bg-amber-100 text-amber-800 border-amber-300';
    case 'READY_FOR_PAYMENT':
    case 'PAYMENT_PENDING':
      return 'bg-blue-100 text-blue-800 border-blue-300';
    case 'FAILED':
    case 'CANCELLED':
      return 'bg-rose-100 text-rose-800 border-rose-300';
    default:
      return 'bg-sky-100 text-sky-800 border-sky-300';
  }
}

export function getApprovalBadgeColor(status: ApprovalStatus | string): string {
  switch (status) {
    case 'APPROVED':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    case 'PENDING':
      return 'bg-amber-100 text-amber-800 border-amber-300';
    case 'REJECTED':
      return 'bg-rose-100 text-rose-800 border-rose-300';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-300';
  }
}

export function getPaymentBadgeColor(status: PaymentStatus | string): string {
  switch (status) {
    case 'PAID':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    case 'PAYMENT_PENDING':
      return 'bg-blue-100 text-blue-800 border-blue-300';
    case 'FAILED':
    case 'EXPIRED':
    case 'CANCELLED':
      return 'bg-rose-100 text-rose-800 border-rose-300';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-300';
  }
}
