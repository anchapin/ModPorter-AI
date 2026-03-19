/**
 * Feedback Survey Component
 * Collects user feedback after a successful conversion
 */

import React, { useState } from 'react';
import { API_BASE_URL } from '../../services/api';
import { trackEvent, AnalyticsEventCategory } from '../../services/analytics';
import './FeedbackSurvey.css';

interface FeedbackSurveyProps {
  jobId: string;
  onSubmit?: () => void;
  onSkip?: () => void;
}

export const FeedbackSurvey: React.FC<FeedbackSurveyProps> = ({
  jobId,
  onSubmit,
  onSkip,
}) => {
  const [rating, setRating] = useState<number>(0);
  const [conversionQuality, setConversionQuality] = useState<number>(0);
  const [easeOfUse, setEaseOfUse] = useState<number>(0);
  const [feedback, setFeedback] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (rating === 0) {
      setError('Please provide a rating');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobId,
          feedback_type: 'detailed',
          quality_rating: conversionQuality,
          ease_of_use: easeOfUse,
          comment: feedback,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      // Track the feedback submission
      await trackEvent(
        'feedback_submit',
        AnalyticsEventCategory.FEEDBACK,
        {
          properties: {
            job_id: jobId,
            rating,
            conversion_quality: conversionQuality,
            ease_of_use: easeOfUse,
          },
        }
      );

      setSubmitted(true);
      onSubmit?.();
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onSkip?.();
  };

  if (submitted) {
    return (
      <div className="feedback-survey success">
        <div className="success-icon">✓</div>
        <h3>Thank You!</h3>
        <p>Your feedback helps us improve ModPorter-AI.</p>
      </div>
    );
  }

  return (
    <div className="feedback-survey">
      <div className="survey-header">
        <h3>How was your conversion?</h3>
        <p>Your feedback helps us improve our conversion quality.</p>
      </div>

      <form onSubmit={handleSubmit} className="survey-form">
        {/* Overall Rating */}
        <div className="form-group">
          <label>Overall Experience</label>
          <div className="star-rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                className={`star-btn ${rating >= star ? 'active' : ''}`}
                onClick={() => setRating(star)}
                aria-label={`Rate ${star} stars`}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Conversion Quality */}
        <div className="form-group">
          <label>Conversion Quality (1-5)</label>
          <div className="star-rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                className={`star-btn ${conversionQuality >= star ? 'active' : ''}`}
                onClick={() => setConversionQuality(star)}
                aria-label={`Rate ${star} stars`}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Ease of Use */}
        <div className="form-group">
          <label>Ease of Use (1-5)</label>
          <div className="star-rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                className={`star-btn ${easeOfUse >= star ? 'active' : ''}`}
                onClick={() => setEaseOfUse(star)}
                aria-label={`Rate ${star} stars`}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Open Feedback */}
        <div className="form-group">
          <label htmlFor="feedback">Additional Feedback (Optional)</label>
          <textarea
            id="feedback"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Tell us what you think... What worked well? What could be improved?"
            rows={4}
          />
        </div>

        {/* Error Message */}
        {error && <div className="error-message">{error}</div>}

        {/* Actions */}
        <div className="form-actions">
          <button
            type="button"
            className="skip-btn"
            onClick={handleSkip}
            disabled={isSubmitting}
          >
            Skip
          </button>
          <button
            type="submit"
            className="submit-btn"
            disabled={isSubmitting || rating === 0}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default FeedbackSurvey;
