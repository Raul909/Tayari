'use client';

import { useState } from 'react';

import Icon from '@/components/Icon';
import { RATING_LABELS, sendFeedback } from '@/lib/api';

// A plain 1–5 scale rather than a row of faces: numbers mean the same thing on
// every platform and in every culture, and the words underneath say what the
// ends of the scale are.
const RATINGS = [1, 2, 3, 4, 5];

const SUBJECTS = ['Bug', 'Suggestion', 'Other'];

export default function FeedbackModal({ onClose }) {
  const [rating, setRating] = useState(null);
  const [subject, setSubject] = useState(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!rating) {
      setError('Please choose a rating.');
      return;
    }
    setError('');
    setSubmitting(true);

    try {
      await sendFeedback(rating, subject, comment);

      setSubmitted(true);
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  return (
    <div className="feedback-overlay" onClick={onClose}>
      <div className="feedback-modal" onClick={e => e.stopPropagation()}>
        <button className="feedback-close" onClick={onClose} aria-label="Close">
          <Icon name="close" size={20} />
        </button>
        
        <h2 className="feedback-title">Your feedback</h2>

        {submitted ? (
          <div className="feedback-success">
            <Icon name="check_circle" size={44} className="success-icon" />
            <p>Thank you for your feedback!</p>
          </div>
        ) : (
          <div className="feedback-body">
            <div className="feedback-section">
              <label id="feedback-rating-label">
                How would you rate this page? <span className="required">*</span>
              </label>
              <div className="feedback-rating" role="radiogroup" aria-labelledby="feedback-rating-label">
                {RATINGS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={rating === value}
                    aria-label={`${value} — ${RATING_LABELS[value]}`}
                    className={`rating-btn ${rating === value ? 'selected' : ''}`}
                    onClick={() => setRating(value)}
                  >
                    {value}
                  </button>
                ))}
              </div>
              <div className="feedback-rating-ends" aria-hidden="true">
                <span>{RATING_LABELS[1]}</span>
                <span>{RATING_LABELS[5]}</span>
              </div>
            </div>

            <div className="feedback-section">
              <label>Subject</label>
              <div className="feedback-subjects">
                {SUBJECTS.map((sub) => (
                  <button
                    key={sub}
                    className={`subject-btn ${subject === sub ? 'selected' : ''}`}
                    onClick={() => setSubject(sub === subject ? null : sub)}
                  >
                    {sub}
                  </button>
                ))}
              </div>
            </div>

            <div className="feedback-section">
              <label>Comment (optional)</label>
              <textarea
                placeholder="What worked, what didn't, or what's missing?"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={4}
              />
            </div>

            {error && <div className="feedback-error">{error}</div>}

            <div className="feedback-footer">
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={submitting || !rating}
              >
                {submitting ? 'Submitting…' : 'Send feedback'}
              </button>
            </div>
            
            <div className="feedback-watermark">
              Powered by <strong>LaunchPixel</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
