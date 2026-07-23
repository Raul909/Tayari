'use client';

import { useState } from 'react';

import { sendFeedback } from '@/lib/api';

const EMOJIS = [
  { value: 1, label: 'Angry', icon: '😠' },
  { value: 2, label: 'Sad', icon: '😞' },
  { value: 3, label: 'Neutral', icon: '😐' },
  { value: 4, label: 'Happy', icon: '🙂' },
  { value: 5, label: 'Very Happy', icon: '😄' }
];

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
      setError('Please select an opinion rating.');
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
        <button className="feedback-close" onClick={onClose} aria-label="Close">✕</button>
        
        <h2 className="feedback-title">Your feedback</h2>

        {submitted ? (
          <div className="feedback-success">
            <div className="success-icon">✓</div>
            <p>Thank you for your feedback!</p>
          </div>
        ) : (
          <div className="feedback-body">
            <div className="feedback-section">
              <label>What is your opinion of this page? <span className="required">*</span></label>
              <div className="feedback-emojis">
                {EMOJIS.map((emoji) => (
                  <button
                    key={emoji.value}
                    className={`emoji-btn ${rating === emoji.value ? 'selected' : ''}`}
                    onClick={() => setRating(emoji.value)}
                    title={emoji.label}
                  >
                    {emoji.icon}
                  </button>
                ))}
              </div>
            </div>

            <div className="feedback-section">
              <label>Please select a subject:</label>
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
              <label>Would you like to add a comment?</label>
              <textarea
                placeholder="PLEASE GIVE YOUR FEEDBACK HERE"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={4}
              />
            </div>

            {error && <div className="feedback-error">{error}</div>}

            <div className="feedback-footer">
              <button 
                className="feedback-submit-btn" 
                onClick={handleSubmit}
                disabled={submitting || !rating}
              >
                {submitting ? 'Submitting...' : 'Continue >'}
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
