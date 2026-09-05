import React from 'react';
import { OfferCandidate } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/lib/utils';
import { Award, Star, CheckCircle, Clock, ShieldCheck, ShoppingBag } from 'lucide-react';

interface OfferRankingListProps {
  offers?: OfferCandidate[];
}

export function OfferRankingList({ offers }: OfferRankingListProps) {
  if (!offers || offers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <Award className="w-5 h-5 text-sky-600" />
            Ranked Vendor Offers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">
            No vendor offers discovered yet. AgentX will search the catalog during the discovery phase.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Award className="w-5 h-5 text-sky-600" />
          Discovered & Ranked Vendor Offers ({offers.length})
        </CardTitle>
        <span className="text-xs text-slate-500 font-medium">
          Deterministic Scoring: Price 40% | Lead Time 30% | Rating 20% | GST 10%
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {offers.map((offer, idx) => {
            const isTopRank = idx === 0;
            // Support both backend field names and aliased names
            const productName = offer.product_name || offer.product_title || `Product #${offer.product_id}`;
            const unitPrice = offer.base_price ?? offer.unit_price ?? 0;
            const isEligible = offer.eligibility_status === 'ELIGIBLE' || offer.is_eligible === true;
            const gstOk = offer.gst_verified || offer.gst_status === 'verified';

            return (
              <div
                key={offer.offer_id || `${offer.vendor_id}-${offer.product_id}-${idx}`}
                className={`rounded-xl border p-4 transition-all relative ${
                  isTopRank
                    ? 'border-sky-300 bg-gradient-to-b from-sky-50/50 to-white shadow-sm ring-1 ring-sky-200'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                {/* Rank Badge */}
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full ${
                      isTopRank
                        ? 'bg-sky-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    #{idx + 1} {isEligible ? 'Eligible' : 'Near Match'}
                  </span>

                  <div className="flex items-center gap-1 bg-amber-50 text-amber-700 px-2 py-0.5 rounded text-xs font-semibold border border-amber-200">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>{offer.vendor_rating?.toFixed(1) || '4.5'}</span>
                  </div>
                </div>

                {/* Product & Vendor Title */}
                <div className="mb-3">
                  <h4 className="text-sm font-bold text-slate-900 line-clamp-1 flex items-center gap-1.5">
                    <ShoppingBag className="w-4 h-4 text-slate-400" />
                    {productName}
                  </h4>
                  <p className="text-xs font-medium text-slate-600">{offer.vendor_name}</p>
                  {offer.sku && (
                    <p className="text-[10px] text-slate-400 font-mono">SKU: {offer.sku}</p>
                  )}
                </div>

                {/* Price & Lead Time */}
                <div className="grid grid-cols-2 gap-2 mb-3 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-[11px] text-slate-400 font-medium block">Base Price</span>
                    <span className="text-sm font-bold text-slate-900">
                      {formatINR(unitPrice)}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-400 font-medium block">Lead Time</span>
                    <span className="text-xs font-semibold text-slate-800 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {offer.lead_time_days} days
                    </span>
                  </div>
                </div>

                {/* GST & Certifications */}
                <div className="flex flex-wrap items-center gap-1.5 mb-3">
                  <Badge variant={gstOk ? 'success' : 'outline'}>
                    <ShieldCheck className="w-3 h-3 mr-1" />
                    GST {gstOk ? 'Verified' : 'Unverified'}
                  </Badge>

                  {offer.certifications &&
                    offer.certifications.map((cert) => (
                      <Badge key={cert} variant="info" className="text-[10px]">
                        {cert}
                      </Badge>
                    ))}
                </div>

                {/* Score & Eligibility */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-slate-400 block font-medium">Overall Score</span>
                    <span className="text-base font-extrabold text-sky-700">
                      {((offer.overall_score ?? 0) * 100).toFixed(1)} / 100
                    </span>
                  </div>

                  {isEligible ? (
                    <Badge variant="success">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Eligible
                    </Badge>
                  ) : (
                    <Badge variant="danger">{offer.eligibility_status || 'Ineligible'}</Badge>
                  )}
                </div>

                {/* Eligibility reasons */}
                {offer.eligibility_reasons && offer.eligibility_reasons.length > 0 && (
                  <div className="mt-2 space-y-0.5">
                    {offer.eligibility_reasons.slice(0, 3).map((reason, ri) => (
                      <p key={ri} className="text-[10px] text-slate-500 leading-tight">{reason}</p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
